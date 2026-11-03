"""앞차 선정."""

from app.perception.lateral import lateral_offset_m


def box_area_px(box: list[float]) -> float:
    """박스 넓이를 구한다.

    사용처: LeadSelector.select()가 가장 가까운 차를 고를 때 호출한다.
    입력: box [x1, y1, x2, y2] (px)
    출력: 넓이 (px²)
    """
    x1, y1, x2, y2 = box
    return (x2 - x1) * (y2 - y1)


class LeadSelector:
    """내 차선 정면에 있는 차 중 가장 큰(가까운) 차를 앞차로 고르고, 앞차를 쉽게 바꾸지 않는다.

    직전 프레임의 앞차를 기억해야 해서 클래스로 만들었다.
    """

    def __init__(
        self, car_width_m: float, lead_half_width_m: float, switch_area_ratio: float
    ) -> None:
        """사용처: pipeline.PerceptionStream이 만들어질 때 한 번 만든다.

        입력: car_width_m 가정 차폭 (m, config의 car_width_m),
              lead_half_width_m 앞차 후보로 볼 정면 기준 반폭 (m, config의 lead_half_width_m),
              switch_area_ratio 다른 후보 넓이가 현재 앞차의 이 배 이상일 때만 앞차를 바꾼다
              (config의 lead_switch_area_ratio)
        """
        self.car_width_m = car_width_m
        self.lead_half_width_m = lead_half_width_m
        self.switch_area_ratio = switch_area_ratio
        self._lead_id: int | None = None  # 직전 프레임의 앞차 ID

    def select(self, tracks: dict[int, list[float]], center_x_px: float) -> int | None:
        """이번 프레임의 앞차를 고르고 기억한다.

        사용처: A(인식) 단계. pipeline.perceive_frame()이 매 프레임 호출한다.
        입력: tracks {트래킹 ID: [x1, y1, x2, y2] (px)}, center_x_px 정면 x (px)
        출력: 앞차의 트래킹 ID, 없으면 None
        주의: 차 중심이 정면에서 lead_half_width_m 안에 있어야 후보가 된다. 차선 경계에 걸친
              옆 차선 차는 후보가 아니다. 급커브에서는 앞차가 정면에서 벗어나 놓칠 수 있다.
        """
        # 옆 거리 절댓값이 반폭 이하(경계 포함)인 차만 후보로 둔다
        candidates = {
            track_id: box
            for track_id, box in tracks.items()
            if abs(lateral_offset_m(box, center_x_px, self.car_width_m)) <= self.lead_half_width_m
        }
        if not candidates:
            self._lead_id = None
            return None

        # 같은 차선이면 박스가 클수록 가깝다
        biggest_id = max(candidates, key=lambda track_id: box_area_px(candidates[track_id]))
        # 두 차의 크기가 비슷하면 판정이 프레임마다 뒤집히므로, 현재 앞차가 아직 후보이고
        # 다른 차가 확실히 크지 않으면(switch_area_ratio배 미만) 현재 앞차를 유지한다
        if self._lead_id in candidates:
            current_area = box_area_px(candidates[self._lead_id])
            if box_area_px(candidates[biggest_id]) < self.switch_area_ratio * current_area:
                biggest_id = self._lead_id

        self._lead_id = biggest_id
        return biggest_id
