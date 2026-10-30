"""눈으로 확인하기 위한 디버그 그림."""

import cv2
import numpy as np

# 색 (BGR)
COLOR_TRAPEZOID = (255, 200, 0)
COLOR_VEHICLE = (180, 180, 180)
COLOR_LEAD = (0, 0, 255)
COLOR_CUT_IN = (0, 165, 255)


def draw_debug(
    frame: np.ndarray,
    tracks: dict[int, list[float]],
    trapezoid_px: np.ndarray,
    lead_id: int | None,
    cut_in: bool,
) -> np.ndarray:
    """사다리꼴, 차량 박스와 ID, 앞차, 끼어들기 표시를 그린다.

    사용처: pipeline.analyze_video()가 debug_video_path를 받았을 때 매 프레임 호출한다.
    입력: frame 원본 BGR 이미지, tracks {ID: 박스(px)}, trapezoid_px (px),
          lead_id 앞차 ID 또는 None, cut_in 끼어들기 여부
    출력: 그림을 그린 새 이미지 (원본은 바꾸지 않음)
    """
    canvas = frame.copy()
    cv2.polylines(canvas, [trapezoid_px.astype(np.int32)], True, COLOR_TRAPEZOID, 2)

    # 앞차는 빨간색, 나머지는 회색으로 박스와 ID를 그린다
    for track_id, box in tracks.items():
        x1, y1, x2, y2 = (int(v) for v in box)
        color = COLOR_LEAD if track_id == lead_id else COLOR_VEHICLE
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
        cv2.putText(canvas, f"id {track_id}", (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    if cut_in:
        cv2.putText(canvas, "CUT-IN", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, COLOR_CUT_IN, 3)
    return canvas
