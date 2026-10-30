"""A(인식) 전체 흐름: 영상 → 프레임별 PerceptionResult."""

import cv2
import numpy as np

from app.perception.cut_in import CutInDetector
from app.perception.debug import draw_debug
from app.perception.detect import crop_hood, load_detector, track_vehicles
from app.perception.lane import trapezoid_to_px
from app.perception.lead import select_lead
from app.schemas import LeadVehicle, PerceptionResult


def perceive_frame(
    tracks: dict[int, list[float]],
    frame_idx: int,
    fps: float,
    trapezoid_px: np.ndarray,
    cut_in_detector: CutInDetector,
) -> PerceptionResult:
    """한 프레임의 트래킹 결과로 앞차와 끼어들기를 정해 A → B 형식으로 만든다.

    사용처: analyze_video()가 매 프레임 호출한다. YOLO 없이 가짜 tracks로 테스트할 수 있다.
    입력: tracks {ID: [x1, y1, x2, y2] (px)}, frame_idx 프레임 번호, fps 초당 프레임 수,
          trapezoid_px 내 차선 사다리꼴 (px), cut_in_detector 영상 단위로 만든 판단기
    출력: PerceptionResult
    """
    lead_id = select_lead(tracks, trapezoid_px)
    lead = LeadVehicle(id=lead_id, box=tracks[lead_id]) if lead_id is not None else None
    cut_in = cut_in_detector.update(tracks, trapezoid_px)
    return PerceptionResult(frame=frame_idx, time=frame_idx / fps, lead=lead, cut_in=cut_in)


def analyze_video(
    video_path: str,
    weights_path: str,
    perception_cfg: dict,
    debug_video_path: str | None = None,
) -> list[PerceptionResult]:
    """영상 하나를 처음부터 끝까지 인식한다.

    사용처: C의 analyze API가 호출할 A의 진입 함수. 지금은 scripts/run_perception.py가 호출한다.
    입력: video_path 영상 경로, weights_path YOLO 가중치 경로,
          perception_cfg config.yaml의 perception 섹션,
          debug_video_path 디버그 영상 저장 경로 (None이면 저장 안 함)
    출력: 프레임별 PerceptionResult 리스트
    """
    model = load_detector(weights_path)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_w_px = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h_px = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    trapezoid_px = trapezoid_to_px(perception_cfg["lane_trapezoid"], frame_w_px, frame_h_px)
    cut_in_detector = CutInDetector(perception_cfg["cut_in_frames"])

    writer = None
    if debug_video_path is not None:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(debug_video_path, fourcc, fps, (frame_w_px, frame_h_px))

    results: list[PerceptionResult] = []
    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        # 검출 → 앞차·끼어들기 판단 순서로 한 프레임을 처리한다
        cropped = crop_hood(frame, perception_cfg["hood_ratio"])
        tracks = track_vehicles(
            model, cropped, perception_cfg["conf_threshold"], perception_cfg["tracker"]
        )
        result = perceive_frame(tracks, frame_idx, fps, trapezoid_px, cut_in_detector)
        results.append(result)

        if writer is not None:
            lead_id = result.lead.id if result.lead else None
            writer.write(draw_debug(frame, tracks, trapezoid_px, lead_id, result.cut_in))
        frame_idx += 1

    cap.release()
    if writer is not None:
        writer.release()
    return results
