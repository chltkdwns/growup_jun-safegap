"""YOLO 차량 검출과 ByteTrack 트래킹."""

import numpy as np
from ultralytics import YOLO

# COCO 클래스 번호: 2 승용차, 5 버스, 7 트럭
VEHICLE_CLASS_IDS = [2, 5, 7]


def load_detector(weights_path: str) -> YOLO:
    """사전학습 YOLO 모델을 불러온다.

    사용처: pipeline.analyze_video()가 영상 하나에 한 번 호출한다.
    입력: weights_path 가중치 파일 경로 (config의 paths.yolo_weights)
    출력: YOLO 모델
    주의: 트래커 상태가 모델 안에 남으므로 영상마다 새로 불러온다.
    """
    return YOLO(weights_path)


def crop_hood(frame: np.ndarray, hood_ratio: float) -> np.ndarray:
    """화면 아래쪽 본넷 영역을 잘라낸다.

    사용처: pipeline.analyze_video()가 검출 전에 매 프레임 호출한다.
    입력: frame (H, W, 3) BGR 이미지, hood_ratio 본넷 높이 비율 (0~1, config)
    출력: 위쪽만 남긴 이미지. 위에서부터 자르므로 박스 좌표는 원본과 같다.
    """
    # 본넷에 비친 반사가 차로 잘못 검출되는 것을 막는다
    keep_h_px = int(frame.shape[0] * (1 - hood_ratio))
    return frame[:keep_h_px]


def track_vehicles(
    model: YOLO, frame: np.ndarray, conf_threshold: float, tracker: str
) -> dict[int, list[float]]:
    """한 프레임에서 차량을 검출하고 트래킹 ID를 붙인다.

    사용처: A(인식) 단계. pipeline.analyze_video()가 매 프레임 호출한다.
    입력: model YOLO 모델, frame 본넷을 자른 BGR 이미지,
          conf_threshold 검출 신뢰도 최소값 (0~1), tracker 트래커 설정 파일 이름
    출력: {트래킹 ID: [x1, y1, x2, y2] (px)}
    주의: 트래커가 아직 ID를 붙이지 않은 박스는 결과에서 빠진다.
    """
    # persist=True: 이전 프레임의 트래킹 상태를 이어서 써서 같은 차에 같은 ID를 붙인다
    result = model.track(
        frame,
        persist=True,
        tracker=tracker,
        classes=VEHICLE_CLASS_IDS,
        conf=conf_threshold,
        verbose=False,
    )[0]
    if result.boxes.id is None:
        return {}
    track_ids = result.boxes.id.int().tolist()
    boxes = result.boxes.xyxy.tolist()
    return dict(zip(track_ids, boxes))
