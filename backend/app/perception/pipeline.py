"""A(인식) 전체 흐름: 영상 → 프레임별 PerceptionFrame."""

import cv2
import numpy as np

from app.perception.cut_in import CutInDetector
from app.perception.debug import draw_debug
from app.perception.detect import crop_hood, load_detector, track_vehicles
from app.perception.lead import LeadSelector
from app.schemas import LeadCar, PerceptionFrame


def perceive_frame(
    tracks: dict[int, list[float]],
    frame_idx: int,
    time_s: float,
    center_x_px: float,
    lead_selector: LeadSelector,
    cut_in_detector: CutInDetector,
    frame_w_px: int,
) -> PerceptionFrame:
    """한 프레임의 트래킹 결과로 앞차와 끼어들기를 정해 A → B 형식으로 만든다.

    사용처: PerceptionStream.process()가 매 프레임 호출한다. YOLO 없이 가짜 tracks로 테스트할 수 있다.
    입력: tracks {ID: [x1, y1, x2, y2] (px)}, frame_idx 프레임 번호, time_s 프레임 촬영 시각 (초),
          center_x_px 정면 x (px), lead_selector·cut_in_detector 영상 단위로 만든 판단기,
          frame_w_px 프레임 너비 (px)
    출력: PerceptionFrame
    """
    lead_id = lead_selector.select(tracks, center_x_px)
    lead = LeadCar(id=lead_id, box=tracks[lead_id]) if lead_id is not None else None
    cut_in = cut_in_detector.update(tracks, center_x_px, frame_w_px)
    return PerceptionFrame(frame=frame_idx, time=time_s, lead=lead, cut_in=cut_in)


class PerceptionStream:
    """프레임을 한 장씩 받아 PerceptionFrame을 돌려주는 인식기.

    모델 트래커, LeadSelector, CutInDetector가 프레임 사이 상태를 가져서 클래스로 만들었다.
    영상 파일(analyze_video)과 실시간 입력이 같은 코드를 쓰게 하려는 것이다.
    """

    def __init__(
        self, weights_path: str, perception_cfg: dict, frame_w_px: int, frame_h_px: int
    ) -> None:
        """사용처: analyze_video()가 영상 하나에 한 번 만든다. 실시간에서는 연결 하나에 한 번 만든다.

        입력: weights_path YOLO 가중치 경로, perception_cfg config.yaml의 perception 섹션,
              frame_w_px·frame_h_px 입력 프레임 크기 (px, 연결 동안 바뀌지 않는다고 가정)
        주의: 트래커 상태가 모델 안에 남으므로 영상(연결)마다 새로 만든다.
        """
        self.perception_cfg = perception_cfg
        self.frame_w_px = frame_w_px
        # 카메라마다 다른 본넷 높이와 정면 위치는 config(카메라 설정 파일로 덮어쓰기)에서 읽는다
        self.hood_ratio = perception_cfg["hood_ratio"]
        self.hood_y_px = int(frame_h_px * (1 - self.hood_ratio))
        self.center_x_px = perception_cfg["center_x_ratio"] * frame_w_px
        self.car_width_m = perception_cfg["car_width_m"]
        self.model = load_detector(weights_path)
        self.lead_selector = LeadSelector(
            self.car_width_m,
            perception_cfg["lead_half_width_m"],
            perception_cfg["lead_switch_area_ratio"],
        )
        self.cut_in_detector = CutInDetector(
            perception_cfg["cut_in_frames"],
            self.car_width_m,
            perception_cfg["lane_half_width_m"],
            perception_cfg["cut_in_zone_m"],
            perception_cfg["cut_in_move_m"],
            perception_cfg["cut_in_min_box_w_px"],
        )
        self.last_tracks: dict[int, list[float]] = {}  # 직전 프레임의 트래킹 결과 (디버그 영상용)

    def process(self, frame: np.ndarray, frame_idx: int, time_s: float) -> PerceptionFrame:
        """프레임 한 장을 인식해 앞차와 끼어들기 결과를 돌려준다.

        사용처: A(인식) 단계. analyze_video()가 영상의 매 프레임 호출한다.
        입력: frame (H, W, 3) BGR 이미지, frame_idx 프레임 번호, time_s 촬영 시각 (초)
        출력: PerceptionFrame
        주의: 프레임 순서대로 호출해야 한다 (트래킹과 끼어들기가 이전 프레임을 쓴다).
        """
        # 검출 → 앞차·끼어들기 판단 순서로 한 프레임을 처리한다
        cropped = crop_hood(frame, self.hood_ratio)
        self.last_tracks = track_vehicles(
            self.model,
            cropped,
            self.perception_cfg["conf_threshold"],
            self.perception_cfg["tracker"],
            self.perception_cfg["nms_iou"],
            self.perception_cfg["imgsz"],
        )
        return perceive_frame(
            self.last_tracks,
            frame_idx,
            time_s,
            self.center_x_px,
            self.lead_selector,
            self.cut_in_detector,
            self.frame_w_px,
        )


def analyze_video(
    video_path: str,
    weights_path: str,
    perception_cfg: dict,
    debug_video_path: str | None = None,
) -> list[PerceptionFrame]:
    """영상 하나를 처음부터 끝까지 인식한다.

    사용처: C의 analyze API가 호출할 A의 진입 함수. 지금은 scripts/run_perception.py와
            scripts/analyze_and_judge.py가 호출한다.
    입력: video_path 영상 경로, weights_path YOLO 가중치 경로,
          perception_cfg config.yaml의 perception 섹션,
          debug_video_path 디버그 영상 저장 경로 (None이면 저장 안 함)
    출력: 프레임별 PerceptionFrame 리스트
    주의: 촬영 시각은 frame_idx ÷ fps로 계산한다 (영상 파일은 프레임 간격이 일정하다고 본다).
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_w_px = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h_px = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    stream = PerceptionStream(weights_path, perception_cfg, frame_w_px, frame_h_px)

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

        result = stream.process(frame, frame_idx, frame_idx / fps)
        results.append(result)

        if writer is not None:
            lead_id = result.lead.id if result.lead else None
            writer.write(
                draw_debug(
                    frame,
                    stream.last_tracks,
                    stream.center_x_px,
                    stream.car_width_m,
                    lead_id,
                    result.cut_in,
                    stream.hood_y_px,
                )
            )
        frame_idx += 1

    cap.release()
    if writer is not None:
        writer.release()
    return results
