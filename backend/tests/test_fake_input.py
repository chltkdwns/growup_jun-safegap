import json
from pathlib import Path

FPS = 30


def load(name):
    path = Path("tests/fixtures") / f"fake_{name}.jsonl"
    return [json.loads(line) for line in path.open()]


def box_w(row):
    x1, _, x2, _ = row["lead"]["box"]
    return x2 - x1


def simple_ttc(prev, cur):
    # TTC = 폭 ÷ 폭 증가 속도 (EMA 없는 가장 단순한 버전)
    dw = (box_w(cur) - box_w(prev)) * FPS
    return box_w(cur) / dw if dw > 0 else None


def test_approach_ttc_matches_truth():
    rows = load("approach")
    i = 60                          # t = 2초 → 정답 거리 30m, 정답 TTC 3초
    ttc = simple_ttc(rows[i - 1], rows[i])
    assert abs(ttc - 3.0) < 0.05


def test_keep_and_away_have_no_ttc():
    for name in ["keep", "away"]:
        rows = load(name)
        assert simple_ttc(rows[59], rows[60]) is None

def test_estimator_matches_truth_and_handles_noise():
    from app.judgment.ttc import TTCEstimator

    # 노이즈 없음: t=2초에서 정답 TTC 3초와 일치
    est = TTCEstimator(fps=FPS, window=20, max_ttc_s=10)
    out = [est.update(box_w(r)) for r in load("approach")]
    assert abs(out[60] - 3.0) < 0.05

    # 박스 떨림 1px: 2~3초 구간에서 정답과의 차이가 1초 미만
    est = TTCEstimator(fps=FPS, window=20, max_ttc_s=10)
    out = [est.update(box_w(r)) for r in load("approach_noisy")]
    for i in range(60, 91):
        truth = (50 - 10 * i / FPS) / 10
        assert abs(out[i] - truth) < 1.0

    # 유지·멀어짐: TTC 없음
    for name in ["keep", "away"]:
        est = TTCEstimator(fps=FPS, window=20, max_ttc_s=10)
        out = [est.update(box_w(r)) for r in load(name)]
        assert out[60] is None