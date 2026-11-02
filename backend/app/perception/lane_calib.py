"""영상마다 소실점과 본넷 경계를 찾아 내 차선 사다리꼴을 자동으로 정한다."""

import cv2
import numpy as np

from app.perception.lane import trapezoid_to_px

# 차선 직선 찾기 (Canny 테두리 → 확률적 Hough 변환) 설정. 카메라와 무관해서 상수로 둔다.
CANNY_LOW = 60
CANNY_HIGH = 160
HOUGH_THRESHOLD = 40  # 직선으로 인정할 최소 투표 수
HOUGH_MIN_LEN_PX = 50  # 너무 짧은 조각은 잡음이라 버린다
HOUGH_MAX_GAP_PX = 20  # 점선 차선을 한 직선으로 잇기 위한 최대 간격
SEARCH_TOP_RATIO = 0.35  # 화면 위쪽(하늘·건물)은 차선이 없어서 보지 않는다
LANE_ANGLE_MIN_DEG = 20  # 거의 수평인 선(정지선, 가드레일 위)은 차선이 아니다
LANE_ANGLE_MAX_DEG = 70  # 거의 수직인 선(전봇대, 건물)은 차선이 아니다

# 소실점 RANSAC 설정
RANSAC_ITERATIONS = 2000
RANSAC_TOL_DEG = 1.5  # 직선이 소실점을 향한다고 볼 최대 각도 차이
RANSAC_SEED = 0  # 같은 영상이면 항상 같은 결과가 나오게 고정


class CalibrationError(Exception):
    """사다리꼴과 본넷 경계를 정하지 못했을 때 내는 오류.

    틀린 기본값으로 조용히 넘어가면 결과 수치가 틀려도 알 수 없어서, 멈추고 알려 준다.
    """


def sample_frames(video_path: str, n_frames: int) -> list[np.ndarray]:
    """영상 전체에서 고르게 n_frames장을 뽑는다.

    사용처: calibrate_trapezoid()가 영상 하나에 한 번 호출한다.
    입력: video_path 영상 경로, n_frames 뽑을 장 수 (config의 calib_sample_frames)
    출력: BGR 이미지 리스트 (못 읽은 프레임은 빠짐)
    주의: 처음 몇 초만 보면 신호 대기처럼 서 있는 장면만 볼 수 있어 영상 전체에서 뽑는다.
    """
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    for idx in np.linspace(0, max(total - 1, 0), n_frames).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if ok:
            frames.append(frame)
    cap.release()
    return frames


def find_lane_segments(frame: np.ndarray) -> np.ndarray:
    """한 프레임에서 차선 후보 직선 조각을 찾는다.

    사용처: estimate_vanishing_point()가 뽑은 프레임마다 호출한다.
    입력: frame (H, W, 3) BGR 이미지
    출력: (N, 4) 배열 [x1, y1, x2, y2] (px). 없으면 (0, 4)
    """
    h_px = frame.shape[0]
    gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    edges = cv2.Canny(gray, CANNY_LOW, CANNY_HIGH)
    edges[: int(h_px * SEARCH_TOP_RATIO)] = 0
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        HOUGH_THRESHOLD,
        minLineLength=HOUGH_MIN_LEN_PX,
        maxLineGap=HOUGH_MAX_GAP_PX,
    )
    if lines is None:
        return np.zeros((0, 4))
    segs = lines.reshape(-1, 4).astype(float)
    # 기울기가 차선다운 조각만 남긴다
    angle_deg = np.degrees(np.abs(np.arctan2(segs[:, 3] - segs[:, 1], segs[:, 2] - segs[:, 0])))
    angle_deg = np.minimum(angle_deg, 180 - angle_deg)
    keep = (angle_deg > LANE_ANGLE_MIN_DEG) & (angle_deg < LANE_ANGLE_MAX_DEG)
    return segs[keep]


def estimate_vanishing_point(
    segments: np.ndarray, frame_w_px: int, frame_h_px: int, min_inliers: int
) -> tuple[float, float] | None:
    """차선 조각들이 가장 많이 모이는 점(소실점)을 RANSAC으로 찾는다.

    사용처: calibrate_trapezoid()가 영상 하나에 한 번 호출한다.
    입력: segments (N, 4) 직선 조각 (px), 프레임 너비·높이 (px),
          min_inliers 소실점으로 인정할 최소 조각 수 (config의 vp_min_inliers)
    출력: 소실점 (x, y) (px). 차선이 부족하면 None
    주의: 정차 중이거나 차선이 안 보이는 시내 영상에서는 None이 나온다.
    """
    if len(segments) < 2:
        return None
    x1, y1, x2, y2 = segments.T
    direction = np.c_[x2 - x1, y2 - y1]
    direction /= np.linalg.norm(direction, axis=1, keepdims=True)
    mid = np.c_[(x1 + x2) / 2, (y1 + y2) / 2]

    rng = np.random.default_rng(RANSAC_SEED)
    best_point, best_count = None, 0
    for _ in range(RANSAC_ITERATIONS):
        # 조각 두 개를 골라 연장선의 교점을 후보로 만든다
        i, j = rng.choice(len(segments), 2, replace=False)
        mat = np.array([direction[i], -direction[j]]).T
        if abs(np.linalg.det(mat)) < 1e-3:  # 평행하면 교점이 없다
            continue
        t = np.linalg.solve(mat, mid[j] - mid[i])
        point = mid[i] + t[0] * direction[i]
        # 소실점은 화면 안, 아래쪽 본넷보다 위에 있어야 한다
        if not (0 < point[0] < frame_w_px and 0 < point[1] < frame_h_px * 0.7):
            continue
        # 각 조각이 후보점을 향하는지 각도로 센다
        to_point = point - mid
        to_point /= np.linalg.norm(to_point, axis=1, keepdims=True) + 1e-9
        cos = np.clip(np.abs((to_point * direction).sum(axis=1)), 0, 1)
        count = int((np.degrees(np.arccos(cos)) < RANSAC_TOL_DEG).sum())
        if count > best_count:
            best_point, best_count = point, count
    if best_count < min_inliers:
        return None
    return float(best_point[0]), float(best_point[1])


def toward_vp_mask(segments: np.ndarray, vp_px: tuple[float, float], tol_deg: float) -> np.ndarray:
    """직선 조각마다 소실점을 향하는지 표시한다.

    사용처: estimate_hood_ratio()와 lane_track.LaneTracker.update()가 차선 조각만 고를 때 호출한다.
    입력: segments (N, 4) 직선 조각 (px), vp_px 소실점 (px), tol_deg 허용 각도 차이 (도)
    출력: (N,) bool 배열. 소실점을 향하면 True
    """
    x1, y1, x2, y2 = segments.T
    direction = np.c_[x2 - x1, y2 - y1]
    direction /= np.linalg.norm(direction, axis=1, keepdims=True) + 1e-9
    mid = np.c_[(x1 + x2) / 2, (y1 + y2) / 2]
    to_vp = np.asarray(vp_px) - mid
    to_vp /= np.linalg.norm(to_vp, axis=1, keepdims=True) + 1e-9
    cos = np.clip(np.abs((to_vp * direction).sum(axis=1)), 0, 1)
    return np.degrees(np.arccos(cos)) < tol_deg


def estimate_hood_ratio(
    segments: np.ndarray, vp_px: tuple[float, float], frame_h_px: int, percentile: float
) -> float:
    """도로 위 차선 조각이 끝나는 높이로 본넷 경계를 찾는다.

    사용처: calibrate_trapezoid()가 소실점을 찾은 뒤 한 번 호출한다.
    입력: segments (N, 4) 영상 전체에서 모은 직선 조각 (px), vp_px 소실점 (px),
          frame_h_px 프레임 높이 (px), percentile 차선 조각 아래 끝 y의 백분위 (config)
    출력: hood_ratio 화면 아래에서 본넷이 차지하는 높이 비율 (0~1)
    주의: 본넷에 비친 차선은 거꾸로 비쳐서 소실점을 향하지 않으므로 빠진다.
          최댓값 대신 백분위를 쓰는 이유는 몇 개 튀는 조각(와이퍼, 반사)에 끌려가지 않게 하려고다.
    """
    # 도로 위 차선은 소실점을 향하고 본넷 경계에서 끊긴다
    lane_segs = segments[toward_vp_mask(segments, vp_px, RANSAC_TOL_DEG)]
    bottom_y_px = np.maximum(lane_segs[:, 1], lane_segs[:, 3])
    hood_top_y_px = np.percentile(bottom_y_px, percentile)
    return float(1 - hood_top_y_px / frame_h_px)


def trapezoid_from_vp(
    vp_px: tuple[float, float],
    frame_w_px: int,
    frame_h_px: int,
    hood_ratio: float,
    lane_half_width_ratio: float,
    lane_top_ratio: float,
) -> np.ndarray:
    """소실점과 본넷 높이로 내 차선 사다리꼴을 만든다.

    사용처: calibrate_trapezoid()가 소실점을 찾았을 때 호출한다.
    입력: vp_px 소실점 (px), 프레임 너비·높이 (px), hood_ratio 본넷 높이 비율 (config),
          lane_half_width_ratio 아래 변 반폭 / 화면 너비 (config),
          lane_top_ratio 위 변 위치. 소실점(0)~본넷(1) 사이 비율 (config)
    출력: (4, 2) float32 배열 (px). 왼쪽 위 → 오른쪽 위 → 오른쪽 아래 → 왼쪽 아래
    주의: 내 차가 차선 가운데를 달린다고 가정한다. 차선 변경 중에는 어긋난다.
    """
    vp_x, vp_y = vp_px
    # 아래 변은 본넷 경계, 좌우 끝은 소실점 바로 아래에서 반폭만큼
    bottom_y = frame_h_px * (1 - hood_ratio)
    half_w = frame_w_px * lane_half_width_ratio
    bottom_left, bottom_right = vp_x - half_w, vp_x + half_w
    # 차선 경계는 소실점으로 모이므로 위 변 꼭짓점도 같은 직선 위에 둔다
    top_y = vp_y + lane_top_ratio * (bottom_y - vp_y)
    shrink = (top_y - vp_y) / (bottom_y - vp_y)
    top_left = vp_x + (bottom_left - vp_x) * shrink
    top_right = vp_x + (bottom_right - vp_x) * shrink
    return np.array(
        [
            [top_left, top_y],
            [top_right, top_y],
            [bottom_right, bottom_y],
            [bottom_left, bottom_y],
        ],
        dtype=np.float32,
    )


def calibrate_trapezoid(
    video_path: str, frame_w_px: int, frame_h_px: int, perception_cfg: dict
) -> tuple[np.ndarray, tuple[float, float] | None, float]:
    """영상 하나의 내 차선 사다리꼴과 본넷 비율을 정한다. 못 정하면 CalibrationError를 낸다.

    사용처: pipeline.analyze_video()가 영상 처리를 시작하기 전에 한 번 호출한다.
    입력: video_path 영상 경로, 프레임 너비·높이 (px), perception_cfg config의 perception 섹션
          (auto_lane이 false면 카메라 설정 파일의 lane_trapezoid, hood_ratio를 쓴다)
    출력: (사다리꼴 (4, 2) px, 찾은 소실점 (px) 또는 None, hood_ratio 본넷 비율 (0~1))
    주의: 카메라마다 위치가 달라서 기본값을 두지 않는다. 자동 보정이 실패하면
          카메라 설정 파일(--camera)로 값을 줘야 한다.
    """
    # 수동 모드: 카메라 설정 파일에 적힌 값을 그대로 쓴다
    if not perception_cfg["auto_lane"]:
        trapezoid_ratio = perception_cfg.get("lane_trapezoid")
        hood_ratio = perception_cfg.get("hood_ratio")
        if trapezoid_ratio is None or hood_ratio is None:
            raise CalibrationError(
                "auto_lane이 false인데 lane_trapezoid 또는 hood_ratio가 없습니다. "
                "카메라 설정 파일(--camera)에 적어 주세요. 예: configs/blackbox_2.yaml"
            )
        return trapezoid_to_px(trapezoid_ratio, frame_w_px, frame_h_px), None, hood_ratio

    frames = sample_frames(video_path, perception_cfg["calib_sample_frames"])
    segments = np.concatenate([find_lane_segments(f) for f in frames] or [np.zeros((0, 4))])
    vp_px = estimate_vanishing_point(
        segments, frame_w_px, frame_h_px, perception_cfg["vp_min_inliers"]
    )
    if vp_px is None:
        raise CalibrationError(
            f"소실점을 못 찾았습니다 (차선 조각 {len(segments)}개, 필요한 최소 지지 "
            f"{perception_cfg['vp_min_inliers']}개). 카메라 설정 파일(--camera)로 "
            "lane_trapezoid, hood_ratio를 주세요. 예: configs/blackbox_2.yaml"
        )
    hood_ratio = perception_cfg.get("hood_ratio")
    if perception_cfg["auto_hood"]:
        hood_ratio = estimate_hood_ratio(
            segments, vp_px, frame_h_px, perception_cfg["hood_lane_percentile"]
        )
    if hood_ratio is None:
        raise CalibrationError("auto_hood가 false인데 hood_ratio가 없습니다.")
    trapezoid = trapezoid_from_vp(
        vp_px,
        frame_w_px,
        frame_h_px,
        hood_ratio,
        perception_cfg["lane_half_width_ratio"],
        perception_cfg["lane_top_ratio"],
    )
    return trapezoid, vp_px, hood_ratio
