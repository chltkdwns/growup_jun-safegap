from collections import deque

import numpy as np


class TTCEstimator:
    """앞차 박스 폭으로 TTC(충돌까지 남은 시간, 초)를 계산한다.

    사용처: B(판단) 단계. 앞차 한 대마다 객체 하나를 만들고, 매 프레임 update()를 호출한다.
    입력: box_w_px 앞차 박스 폭(px)
    출력: TTC(초). 가까워지지 않거나, max_ttc_s보다 크거나, 프레임이 아직 부족하면 None
    주의: 앞차 ID가 바뀌면 이전 차의 폭과 섞이므로 reset()을 호출해야 한다.

    원리: 거리는 박스 폭에 반비례하므로 1/폭은 거리에 비례한다.
    상대속도가 일정하면 1/폭은 시간에 대해 직선이 되고,
    최근 N프레임에 직선을 맞춘 뒤 "이 직선이 0이 되는 데 남은 시간"이 TTC다.
    """

    def __init__(self, fps: float, window: int, max_ttc_s: float):
        self.fps = fps              # 영상 프레임 속도 (config에서 받음)
        self.window = window        # 직선을 맞출 최근 프레임 수 (config에서 받음)
        self.max_ttc_s = max_ttc_s  # 이보다 큰 TTC는 "위험 없음"으로 봄 (config에서 받음)
        self.reset()

    def reset(self) -> None:
        self.inv_w = deque(maxlen=self.window)  # 최근 N프레임의 1/박스 폭

    def update(self, box_w_px: float) -> float | None:
        # 1) 1/폭을 저장 (거리에 비례하는 값)
        self.inv_w.append(1.0 / box_w_px)
        if len(self.inv_w) < self.window:
            return None  # 프레임이 모일 때까지 대기
        # 2) 최근 N프레임에 직선 맞추기: 1/폭 = a + b × 시간
        t_s = np.arange(self.window) / self.fps
        b, a = np.polyfit(t_s, np.array(self.inv_w), 1)
        # 3) 줄어들지 않으면(멀어지거나 유지) 충돌 위험 없음
        if b >= 0:
            return None
        # 4) 현재 값이 0까지 줄어드는 데 걸리는 시간 = TTC
        now = a + b * t_s[-1]
        ttc_s = -now / b
        # 5) 거리가 거의 그대로면 기울기가 0에 가까워 TTC가 비정상적으로 커짐 → 위험 없음
        return ttc_s if ttc_s <= self.max_ttc_s else None
