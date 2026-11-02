"""눈으로 확인하기 위한 디버그 그림."""

import cv2
import numpy as np

from app.perception.lateral import lateral_offset_m

# 색 (BGR)
COLOR_CENTER = (255, 0, 255)
COLOR_VEHICLE = (180, 180, 180)
COLOR_LEAD = (0, 0, 255)
COLOR_CUT_IN = (0, 165, 255)
COLOR_HOOD = (0, 255, 255)


def draw_debug(
    frame: np.ndarray,
    tracks: dict[int, list[float]],
    center_x_px: float,
    car_width_m: float,
    lead_id: int | None,
    cut_in: bool,
    hood_y_px: int,
) -> np.ndarray:
    """정면 기준선, 본넷 경계선, 차량 박스와 ID, 앞차, 끼어들기 표시를 그린다.

    사용처: pipeline.analyze_video()가 debug_video_path를 받았을 때 매 프레임 호출한다.
    입력: frame 원본 BGR 이미지, tracks {ID: 박스(px)}, center_x_px 정면 x (px), car_width_m 가정 차폭 (m),
          lead_id 앞차 ID 또는 None, cut_in 끼어들기 여부, hood_y_px 본넷 경계 높이 (px)
    출력: 그림을 그린 새 이미지 (원본은 바꾸지 않음)
    """
    canvas = frame.copy()
    # 옆 거리(m)를 재는 기준이 되는 정면 x를 세로선으로 보여 준다
    cv2.line(canvas, (int(center_x_px), 0), (int(center_x_px), canvas.shape[0]), COLOR_CENTER, 1)
    # 본넷 경계 아래는 검출에서 잘라내는 영역이라 눈으로 확인할 수 있게 선을 긋는다
    cv2.line(canvas, (0, hood_y_px), (canvas.shape[1], hood_y_px), COLOR_HOOD, 1)

    # 앞차는 빨간색, 나머지는 회색으로 박스와 ID를 그린다
    for track_id, box in tracks.items():
        x1, y1, x2, y2 = (int(v) for v in box)
        color = COLOR_LEAD if track_id == lead_id else COLOR_VEHICLE
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            canvas,
            f"id {track_id} {lateral_offset_m(box, center_x_px, car_width_m):+.1f}m",
            (x1, y1 - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )

    if cut_in:
        cv2.putText(canvas, "CUT-IN", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, COLOR_CUT_IN, 3)
    return canvas
