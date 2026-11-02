"""프레임마다 차선 따라가기 단위 테스트. 검은 화면에 흰 차선을 그려 확인한다.

실행 (backend 폴더에서): python -m pytest tests
"""

import cv2
import numpy as np

from app.perception.lane_calib import trapezoid_from_vp
from app.perception.lane_track import LaneTracker

FRAME_W, FRAME_H = 1000, 1000
VP = (500.0, 400.0)
CFG = {
    "lane_ema_alpha": 1.0,  # 테스트에서는 바로 따라가게 한다
    "lane_width_min_ratio": 0.25,
    "lane_width_max_ratio": 0.6,
}
# 그린 선은 두께가 있어 테두리(Canny)가 선 양쪽에 생기므로 몇 px 어긋날 수 있다
TOL_PX = 30


def lane_frame(left_x: float, right_x: float) -> np.ndarray:
    """소실점에서 y 700의 left_x, right_x로 내려오는 흰 차선 두 개를 그린 화면."""
    frame = np.zeros((FRAME_H, FRAME_W, 3), dtype=np.uint8)
    for x in (left_x, right_x):
        cv2.line(frame, (int(VP[0]), int(VP[1])), (int(x), 700), (255, 255, 255), 6)
    return frame


def start_trapezoid() -> np.ndarray:
    """아래 변 x 300~700, 본넷 경계 y 700인 처음 사다리꼴."""
    return trapezoid_from_vp(VP, FRAME_W, FRAME_H, 0.3, 0.2, 0.1)


def test_tracker_moves_edges_to_visible_lane():
    tracker = LaneTracker(start_trapezoid(), VP, FRAME_W, CFG)
    trap = tracker.update(lane_frame(250, 750))
    # 아래 변 양 끝이 그려진 차선 위치(250, 750) 근처로 옮겨간다
    assert abs(trap[3, 0] - 250) < TOL_PX and abs(trap[2, 0] - 750) < TOL_PX


def test_tracker_keeps_last_edges_when_no_lane():
    tracker = LaneTracker(start_trapezoid(), VP, FRAME_W, CFG)
    tracker.update(lane_frame(250, 750))
    trap = tracker.update(np.zeros((FRAME_H, FRAME_W, 3), dtype=np.uint8))
    assert abs(trap[3, 0] - 250) < TOL_PX and abs(trap[2, 0] - 750) < TOL_PX


def test_tracker_ignores_too_wide_lane():
    tracker = LaneTracker(start_trapezoid(), VP, FRAME_W, CFG)
    # 폭 900px(화면의 90%)는 옆 차선까지 잡은 것으로 보고 무시한다
    trap = tracker.update(lane_frame(50, 950))
    assert np.allclose(trap, start_trapezoid())
