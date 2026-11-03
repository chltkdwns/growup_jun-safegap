"""A(인식) 전체 흐름: 영상 → 프레임별 PerceptionFrame."""

import cv2

from app.perception.cut_in import CutInDetector
from app.perception.debug import draw_debug
from app.perception.detect import crop_hood, load_detector, track_vehicles
from app.perception.lead import select_lead
from app.schemas import LeadCar, PerceptionFrame


def perceive_frame(
    tracks: dict[int, list[float]],
    frame_idx: int,
    fps: float,
    center_x_px: float,
    cut_in_detector: CutInDetector,
    frame_w_px: int,
    car_width_m: float,
    lane_half_width_m: float,
) -> PerceptionFrame:
    """한 프레임의 트래킹 결과로 앞차와 끼어들기를 정해 A → B 형식으로 만든다.

    사용처: analyze_video()가 매 프레임 호출한다. YOLO 없이 가짜 tracks로 테스트할 수 있다.
    입력: tracks {ID: [x1, y1, x2, y2] (px)}, frame_idx 프레임 번호, fps 초당 프레임 수,
          center_x_px 정면 x (px), cut_in_detector 영상 단위로 만든 판단기,
          frame_w_px 프레임 너비 (px), car_width_m 가정 차폭 (m), lane_half_width_m 차선 반폭 (m)
    출력: PerceptionFrame
    """
    lead_id = select_lead(tracks, center_x_px, car_width_m, lane_half_width_m)
    lead = LeadCar(id=lead_id, box=tracks[lead_id]) if lead_id is not None else None
    cut_in = cut_in_detector.update(tracks, center_x_px, frame_w_px)
    return PerceptionFrame(frame=frame_idx, time=frame_idx / fps, lead=lead, cut_in=cut_in)


def analyze_video(
    video_path: str,
    weights_path: str,
    perception_cfg: dict,
    debug_video_path: str | None = None,
) -> list[PerceptionFrame]:
    """영상 하나를 처음부터 끝까지 인식한다.

    사용처: C의 analyze API가 호출할 A의 진입 함수. 지금은 scripts/run_perception.py가 호출한다.
    입력: video_path 영상 경로, weights_path YOLO 가중치 경로,
          perception_cfg config.yaml의 perception 섹션,
          debug_video_path 디버그 영상 저장 경로 (None이면 저장 안 함)
    출력: 프레임별 PerceptionFrame 리스트
    """
    model = load_detector(weights_path)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_w_px = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h_px = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # 카메라마다 다른 본넷 높이와 정면 위치는 config(카메라 설정 파일로 덮어쓰기)에서 읽는다
    hood_ratio = perception_cfg["hood_ratio"]
    hood_y_px = int(frame_h_px * (1 - hood_ratio))
    center_x_px = perception_cfg["center_x_ratio"] * frame_w_px
    car_width_m = perception_cfg["car_width_m"]
    lane_half_width_m = perception_cfg["lane_half_width_m"]
    cut_in_detector = CutInDetector(
        perception_cfg["cut_in_frames"],
        car_width_m,
        lane_half_width_m,
        perception_cfg["cut_in_zone_m"],
        perception_cfg["cut_in_move_m"],
        perception_cfg["cut_in_min_box_w_px"],
    )

    writer = None
    if debug_video_path is not None:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(debug_video_path, fourcc, fps, (frame_w_px, frame_h_px))

    results: list[PerceptionFrame] = []
    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        # 검출 → 앞차·끼어들기 판단 순서로 한 프레임을 처리한다
        cropped = crop_hood(frame, hood_ratio)
        tracks = track_vehicles(
            model,
            cropped,
            perception_cfg["conf_threshold"],
            perception_cfg["tracker"],
            perception_cfg["nms_iou"],
        )
        result = perceive_frame(
            tracks,
            frame_idx,
            fps,
            center_x_px,
            cut_in_detector,
            frame_w_px,
            car_width_m,
            lane_half_width_m,
        )
        results.append(result)

        if writer is not None:
            lead_id = result.lead.id if result.lead else None
            writer.write(
                draw_debug(
                    frame, tracks, center_x_px, car_width_m, lead_id, result.cut_in, hood_y_px
                )
            )
        frame_idx += 1

    cap.release()
    if writer is not None:
        writer.release()
    return results
