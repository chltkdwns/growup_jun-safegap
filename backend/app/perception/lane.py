"""내 차선 사다리꼴 영역과 박스 위치 계산."""

import cv2
import numpy as np


def bottom_center(box: list[float]) -> tuple[float, float]:
    """박스 아래쪽 가운데 점을 구한다.

    사용처: lead.select_lead(), cut_in.CutInDetector.update()가 차 위치를 잴 때 호출한다.
    입력: box [x1, y1, x2, y2] (px)
    출력: (x, y) (px)
    주의: 바퀴가 땅에 닿는 지점이 차선 위치를 가장 잘 나타낸다고 가정한다.
    """
    x1, _, x2, y2 = box
    return ((x1 + x2) / 2, y2)


def trapezoid_to_px(
    trapezoid_ratio: list[list[float]], frame_w_px: int, frame_h_px: int
) -> np.ndarray:
    """설정 파일의 비율 좌표 사다리꼴을 픽셀 좌표로 바꾼다.

    사용처: pipeline.analyze_video()가 영상 크기를 알게 된 뒤 한 번 호출한다.
    입력: trapezoid_ratio 꼭짓점 4개 [[x, y], ...] (0~1), 프레임 너비·높이 (px)
    출력: (4, 2) float32 배열 (px)
    """
    # 비율로 저장해 두면 해상도가 다른 영상에도 같은 설정을 쓸 수 있다
    points = [[x * frame_w_px, y * frame_h_px] for x, y in trapezoid_ratio]
    return np.array(points, dtype=np.float32)


def signed_distance_px(point: tuple[float, float], trapezoid_px: np.ndarray) -> float:
    """점과 사다리꼴 경계 사이의 거리를 부호와 함께 구한다.

    사용처: lead.select_lead()(안에 있는지), cut_in.CutInDetector.update()(다가오는지)
    입력: point (x, y) (px), trapezoid_px (4, 2) 배열 (px)
    출력: 거리 (px). 안쪽이면 양수, 바깥이면 음수, 경계 위면 0
    """
    # cv2.pointPolygonTest는 measureDist=True일 때 부호 있는 거리를 돌려준다
    return cv2.pointPolygonTest(trapezoid_px.reshape(-1, 1, 2), point, True)
