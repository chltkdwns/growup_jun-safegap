"""끼어들기 판단."""

from app.perception.lateral import lateral_offset_m


class CutInDetector:
    """옆 차가 내 차선으로 들어오는지 프레임마다 판단한다.

    차마다 이전 프레임 위치를 기억해야 해서 클래스로 만들었다.
    """

    def __init__(
        self,
        approach_frames: int,
        car_width_m: float,
        lane_half_width_m: float,
        zone_m: float,
        move_m: float,
        min_box_w_px: float,
    ) -> None:
        """사용처: pipeline.analyze_video()가 영상 하나에 한 번 만든다.

        입력: approach_frames 끼어들기로 볼 연속 프레임 수 N (config의 cut_in_frames),
              car_width_m 가정 차폭 (m), lane_half_width_m 내 차선 반폭 (m),
              zone_m 차선 바깥 이 거리(m) 안의 차만 끼어들기 후보 (config의 cut_in_zone_m),
              move_m N프레임 동안 안쪽으로 이만큼(m) 이상 다가와야 끼어들기 (config의 cut_in_move_m),
              min_box_w_px 이보다 폭이 작은 먼 차는 판단하지 않는다 (px, config의 cut_in_min_box_w_px)
        """
        self.approach_frames = approach_frames
        self.car_width_m = car_width_m
        self.lane_half_width_m = lane_half_width_m
        self.zone_m = zone_m
        self.move_m = move_m
        self.min_box_w_px = min_box_w_px
        self._offset_history: dict[int, list[float]] = {}  # 차별 최근 옆 거리(m) 기록

    def update(
        self, tracks: dict[int, list[float]], center_x_px: float, frame_w_px: int
    ) -> bool:
        """이번 프레임에 끼어들기가 있는지 판단하고 차별 기록을 갱신한다.

        사용처: A(인식) 단계. pipeline.perceive_frame()이 매 프레임 호출한다.
        입력: tracks {트래킹 ID: [x1, y1, x2, y2] (px)}, center_x_px 정면 x (px),
              frame_w_px 프레임 너비 (px)
        출력: 끼어들기 여부
        주의: 직전 프레임에 차선 바깥에 있던 차만 본다. 이번 프레임에 안 보인 차의 기록은 지운다.
              처음 나타난 차는 기록이 없어 move_m 이상 움직였는지 알 수 없으므로 끼어들기로 보지 않는다.
              화면 끝에서 잘린 박스와 폭이 작은 먼 박스는 옆 거리가 흔들려서 보지 않는다.
        """
        cut_in = False
        new_history: dict[int, list[float]] = {}

        for track_id, box in tracks.items():
            box_w_px = box[2] - box[0]
            # 잘린 박스와 작은 박스는 폭이 조금만 흔들려도 옆 거리가 크게 변해서 판단에서 뺀다
            if box[0] <= 0 or box[2] >= frame_w_px or box_w_px < self.min_box_w_px:
                continue
            offset_m = lateral_offset_m(box, center_x_px, self.car_width_m)
            # 최근 N+1프레임의 옆 거리만 남긴다 (처음과 지금 사이가 N프레임)
            history = (self._offset_history.get(track_id, []) + [offset_m])[
                -(self.approach_frames + 1) :
            ]
            new_history[track_id] = history
            if len(history) < 2:
                continue

            prev_m = history[-2]
            # 직전엔 차선 바깥, 지금은 차선 안(같은 쪽)이고, 기록 처음 위치보다 move_m 이상
            # 안쪽으로 이동했으면 경계를 넘어 들어온 것이다. 이동량 조건이 없으면 경계 위에
            # 가만히 있는 차가 박스 흔들림 때문에 안팎으로 오갈 때마다 끼어들기로 잡힌다
            crossed = (
                abs(prev_m) > self.lane_half_width_m >= abs(offset_m)
                and prev_m * offset_m > 0
                and abs(history[0]) - abs(offset_m) >= self.move_m
            )
            # N프레임 전엔 차선 바로 바깥(zone_m 이내)이었고, 같은 쪽에서 move_m 이상 다가왔으며
            # 마지막 프레임도 계속 다가오는 중이면 끼어드는 중이다
            approaching = False
            if len(history) == self.approach_frames + 1:
                start_m = history[0]
                in_zone = self.lane_half_width_m < abs(start_m) <= self.lane_half_width_m + self.zone_m
                approaching = (
                    start_m * offset_m > 0
                    and in_zone
                    and abs(start_m) - abs(offset_m) >= self.move_m
                    and abs(prev_m) - abs(offset_m) > 0
                )
            if crossed or approaching:
                cut_in = True

        self._offset_history = new_history
        return cut_in
