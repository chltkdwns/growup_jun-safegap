import json
import random
from pathlib import Path

FPS = 30            # 가짜 영상 프레임 속도
F_PX = 1000         # 가짜 카메라 초점거리(px)
CAR_W_M = 1.8       # 앞차 실제 폭(m)
CENTER_X = 960      # 앞차를 놓을 화면 가로 중앙(px)
BOTTOM_Y = 600      # 앞차 박스 아래쪽 y(px)


def make_scenario(start_m, rel_speed_ms, seconds, noise_px=0.0, seed=0):
    """앞차와의 거리가 일정한 속도로 변하는 A→B 가짜 입력을 만든다.

    rel_speed_ms > 0 이면 가까워짐, < 0 이면 멀어짐.
    noise_px는 박스 폭에 더할 흔들림(표준편차, px).
    """
    rng = random.Random(seed)  # 시드 고정: 매번 같은 데이터
    frames = []
    for i in range(int(seconds * FPS)):
        t = i / FPS
        dist_m = start_m - rel_speed_ms * t                       # 정답 거리
        w = F_PX * CAR_W_M / dist_m + rng.gauss(0, noise_px)      # 핀홀 공식을 거꾸로
        h = w * 0.8                                               # 높이는 폭에 비례한다고 가정
        box = [CENTER_X - w / 2, BOTTOM_Y - h, CENTER_X + w / 2, BOTTOM_Y]
        frames.append({
            "frame": i,
            "time": round(t, 4),
            "lead": {"id": 1, "box": [round(v, 2) for v in box]},
            "cut_in": False,
        })
    return frames


SCENARIOS = {
    "approach": dict(start_m=50, rel_speed_ms=10, seconds=4),             # 접근: TTC가 5초 → 1초로 줄어듦
    "keep": dict(start_m=40, rel_speed_ms=0, seconds=4),                  # 유지: TTC 없음
    "away": dict(start_m=30, rel_speed_ms=-5, seconds=4),                 # 멀어짐: TTC 없음
    "approach_noisy": dict(start_m=50, rel_speed_ms=10, seconds=4, noise_px=1.0),  # 접근 + 박스 떨림
}

if __name__ == "__main__":
    out_dir = Path("tests/fixtures")
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, params in SCENARIOS.items():
        path = out_dir / f"fake_{name}.jsonl"
        with path.open("w") as f:
            for row in make_scenario(**params):
                f.write(json.dumps(row) + "\n")   # 한 줄 = 한 프레임
        print("saved", path)
