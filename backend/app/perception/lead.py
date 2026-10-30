"""앞차 선정."""

import numpy as np

from app.perception.lane import bottom_center, signed_distance_px


def box_area_px(box: list[float]) -> float:
    """박스 넓이를 구한다.

    사용처: select_lead()가 가장 가까운 차를 고를 때 호출한다.
    입력: box [x1, y1, x2, y2] (px)
    출력: 넓이 (px²)
    """
    x1, y1, x2, y2 = box
    return (x2 - x1) * (y2 - y1)


def select_lead(tracks: dict[int, list[float]], trapezoid_px: np.ndarray) -> int | None:
    """내 차선 안에 있는 차 중 가장 큰(가까운) 차를 앞차로 고른다.

    사용처: A(인식) 단계. pipeline.perceive_frame()이 매 프레임 호출한다.
    입력: tracks {트래킹 ID: [x1, y1, x2, y2] (px)}, trapezoid_px 내 차선 사다리꼴 (px)
    출력: 앞차의 트래킹 ID, 없으면 None
    주의: 급커브에서는 사다리꼴이 실제 차선과 어긋나 옆 차선 차를 고를 수 있다.
    """
    # 아래쪽 가운데 점이 사다리꼴 안(경계 포함)에 있는 차만 후보로 둔다
    candidates = {
        track_id: box
        for track_id, box in tracks.items()
        if signed_distance_px(bottom_center(box), trapezoid_px) >= 0
    }
    if not candidates:
        return None
    # 같은 차선이면 박스가 클수록 가깝다
    return max(candidates, key=lambda track_id: box_area_px(candidates[track_id]))
