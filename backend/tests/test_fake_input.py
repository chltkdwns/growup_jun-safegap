import json
from pathlib import Path
from app.judgment.ttc import TTCEstimator

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
    est = TTCEstimator(window_s=0.7, max_ttc_s=10)
    out = [est.update(box_w(r), r["time"]) for r in load("approach")]
    assert abs(out[60] - 3.0) < 0.05

    # 박스 떨림 1px: 2~3초 구간에서 정답과의 차이가 1초 미만
    est = TTCEstimator(window_s=0.7, max_ttc_s=10)
    out = [est.update(box_w(r), r["time"]) for r in load("approach_noisy")]
    for i in range(60, 91):
        truth = (50 - 10 * i / FPS) / 10
        assert abs(out[i] - truth) < 1.0

    # 유지·멀어짐: TTC 없음
    for name in ["keep", "away"]:
        est = TTCEstimator(window_s=0.7, max_ttc_s=10)
        out = [est.update(box_w(r), r["time"]) for r in load(name)]
        assert out[60] is None

def test_estimator_irregular_interval():
    """프레임 간격이 1/30~1/8초로 들쭉날쭉해도(폰 실시간) 정답 TTC(5 - t초)와 일치"""
    from app.judgment.ttc import TTCEstimator

    est = TTCEstimator(window_s=0.7, max_ttc_s=10)
    for r in load("approach_irregular"):
        ttc = est.update(box_w(r), r["time"])
        if ttc is not None:
            assert abs(ttc - (5 - r["time"])) < 0.05


def test_estimator_waits_for_window_s():
    """window_s(0.7초)만큼 지켜보기 전에는 TTC를 내지 않음"""
    from app.judgment.ttc import TTCEstimator

    est = TTCEstimator(window_s=0.7, max_ttc_s=10)
    for r in load("approach_irregular"):
        ttc = est.update(box_w(r), r["time"])
        if r["time"] < 0.7:
            assert ttc is None