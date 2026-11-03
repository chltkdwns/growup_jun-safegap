from collections import deque

import numpy as np

MIN_POINTS = 3  # 직선을 맞추려면 최소 3개 점이 있어야 기울기가 안정적


class TTCEstimator:
    """앞차 박스 폭과 촬영 시각으로 TTC(충돌까지 남은 시간, 초)를 계산한다.

    사용처: B(판단) 단계. 앞차 한 대마다 객체 하나를 만들고, 매 프레임 update()를 호출한다.
    입력: box_w_px 앞차 박스 폭(px), time_s 그 프레임의 촬영 시각(초)
    출력: TTC(초). 가까워지지 않거나, max_ttc_s보다 크거나, 시간이 아직 window_s만큼 안 모였으면 None
    주의: 앞차 ID가 바뀌면 reset()을 호출해야 한다.
          프레임 간격이 일정하지 않아도 된다(폰 실시간 입력). 시간은 늘어나는 순서로 넣는다.

    원리: 1/폭은 거리에 비례한다. 상대속도가 일정하면 1/폭은 시간에 대해 직선이 되고,
    최근 window_s초의 점들에 직선을 맞춘 뒤 "이 직선이 0이 되는 데 남은 시간"이 TTC다.
    """

    def __init__(self, window_s: float, max_ttc_s: float):
        self.window_s = window_s    # 직선을 맞출 최근 시간 길이(초)
        self.max_ttc_s = max_ttc_s  # 이보다 큰 TTC는 "위험 없음"으로 봄
        self.reset()

    def reset(self) -> None:
        self.points = deque()   # (촬영 시각, 1/박스 폭) 목록
        self.start_s = None     # 이 앞차를 처음 본 시각

    def update(self, box_w_px: float, time_s: float) -> float | None:
        # 1) (시각, 1/폭)을 저장하고, window_s보다 오래된 점은 버림
        if self.start_s is None:
            self.start_s = time_s
        self.points.append((time_s, 1.0 / box_w_px))
        while time_s - self.points[0][0] > self.window_s:
            self.points.popleft()
        # 2) window_s만큼 지켜보기 전이거나 점이 너무 적으면 대기
        if time_s - self.start_s < self.window_s or len(self.points) < MIN_POINTS:
            return None
        # 3) 실제 촬영 시각으로 직선 맞추기: 1/폭 = a + b × (시각 - 지금) → 지금 값이 a
        t_s = np.array([p[0] for p in self.points]) - time_s
        inv_w = np.array([p[1] for p in self.points])
        b, a = np.polyfit(t_s, inv_w, 1)
        # 4) 줄어들지 않으면(멀어지거나 유지) 충돌 위험 없음
        if b >= 0:
            return None
        # 5) 지금 값(a)이 0까지 줄어드는 데 걸리는 시간 = TTC
        ttc_s = -a / b
        # 6) 기울기가 0에 가까워 TTC가 비정상적으로 크면 위험 없음
        return ttc_s if ttc_s <= self.max_ttc_s else None