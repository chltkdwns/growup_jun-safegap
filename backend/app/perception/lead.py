"""앞차 선정."""

from app.perception.lateral import lateral_offset_m


def box_area_px(box: list[float]) -> float:
    """박스 넓이를 구한다.

    사용처: select_lead()가 가장 가까운 차를 고를 때 호출한다.
    입력: box [x1, y1, x2, y2] (px)
    출력: 넓이 (px²)
    """
    x1, y1, x2, y2 = box
    return (x2 - x1) * (y2 - y1)


def select_lead(
    tracks: dict[int, list[float]],
    center_x_px: float,
    car_width_m: float,
    lane_half_width_m: float,
) -> int | None:
    """내 차선 폭 안에 있는 차 중 가장 큰(가까운) 차를 앞차로 고른다.

    사용처: A(인식) 단계. pipeline.perceive_frame()이 매 프레임 호출한다.
    입력: tracks {트래킹 ID: [x1, y1, x2, y2] (px)}, center_x_px 정면 x (px),
          car_width_m 가정 차폭 (m), lane_half_width_m 내 차선 반폭 (m, config)
    출력: 앞차의 트래킹 ID, 없으면 None
    주의: 급커브에서는 앞차가 정면에서 벗어나 보여 앞차를 놓칠 수 있다.
    """
    # 옆 거리 절댓값이 차선 반폭 이하(경계 포함)인 차만 후보로 둔다
    candidates = {
        track_id: box
        for track_id, box in tracks.items()
        if abs(lateral_offset_m(box, center_x_px, car_width_m)) <= lane_half_width_m
    }
    if not candidates:
        return None
    # 같은 차선이면 박스가 클수록 가깝다
    return max(candidates, key=lambda track_id: box_area_px(candidates[track_id]))
