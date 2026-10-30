"""끼어들기 판단."""

import numpy as np

from app.perception.lane import bottom_center, signed_distance_px


class CutInDetector:
    """옆 차가 내 차선으로 들어오는지 프레임마다 판단한다.

    차마다 이전 프레임 위치를 기억해야 해서 클래스로 만들었다.
    """

    def __init__(self, approach_frames: int) -> None:
        """사용처: pipeline.analyze_video()가 영상 하나에 한 번 만든다.

        입력: approach_frames 끼어들기로 볼 연속 접근 프레임 수 N (config의 cut_in_frames)
        """
        self.approach_frames = approach_frames
        self._prev_distance_px: dict[int, float] = {}  # 차별 직전 프레임의 경계 거리
        self._approach_count: dict[int, int] = {}  # 차별 연속 접근 프레임 수

    def update(self, tracks: dict[int, list[float]], trapezoid_px: np.ndarray) -> bool:
        """이번 프레임에 끼어들기가 있는지 판단하고 차별 상태를 갱신한다.

        사용처: A(인식) 단계. pipeline.perceive_frame()이 매 프레임 호출한다.
        입력: tracks {트래킹 ID: [x1, y1, x2, y2] (px)}, trapezoid_px 내 차선 사다리꼴 (px)
        출력: 끼어들기 여부
        주의: 직전 프레임에 사다리꼴 바깥에 있던 차만 본다. 처음부터 안에 나타난 차는
              끼어들기로 보지 않는다. 이번 프레임에 안 보인 차의 기록은 지운다.
        """
        cut_in = False
        new_distance: dict[int, float] = {}
        new_count: dict[int, int] = {}

        for track_id, box in tracks.items():
            distance_px = signed_distance_px(bottom_center(box), trapezoid_px)
            new_distance[track_id] = distance_px
            prev_px = self._prev_distance_px.get(track_id)

            # 직전 위치를 모르거나 이미 안에 있던 차는 판단하지 않는다
            if prev_px is None or prev_px >= 0:
                new_count[track_id] = 0
                continue

            # 경계 쪽으로 다가오면 연속 횟수를 늘리고, 아니면 0으로 되돌린다
            approaching = distance_px > prev_px
            new_count[track_id] = self._approach_count.get(track_id, 0) + 1 if approaching else 0

            # 경계를 넘었거나 N프레임 연속으로 다가오면 끼어들기로 본다
            crossed = distance_px >= 0
            if crossed or new_count[track_id] >= self.approach_frames:
                cut_in = True

        self._prev_distance_px = new_distance
        self._approach_count = new_count
        return cut_in
