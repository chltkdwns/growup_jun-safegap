import sys
from pathlib import Path

from app.config import load_config

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from run_kitti_judge import distance_errors_pct, judge_sequence  # noqa: E402

MINI = Path(__file__).resolve().parent / "fixtures" / "kitti_mini"


def test_pinhole_distance_matches_truth_on_mini_kitti():
    results, truth = judge_sequence(MINI, "0000", load_config())
    errs = distance_errors_pct(results, truth)
    assert len(errs) == 10
    assert max(abs(e) for e in errs) < 1.0    # 가짜 데이터는 차폭이 정확히 1.8m라 오차 1% 미만
    assert results[0]["speed_kmh"] == 72.0
