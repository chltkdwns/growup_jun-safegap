import json
import sys
from pathlib import Path

from app.config import load_config
from app.judgment.judge import FrameJudge

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from run_judge import judge_file  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_judge_file_writes_one_line_per_frame(tmp_path):
    cfg = load_config()
    judge = FrameJudge(cfg["judgment"], fps=30, focal_px=1000)
    out = tmp_path / "judged.jsonl"   # pytest가 주는 임시 폴더라 테스트 뒤 자동 삭제

    n = judge_file(FIXTURES / "fake_approach.jsonl", out, judge, speed_kmh=100)

    lines = out.read_text(encoding="utf-8").splitlines()
    assert n == len(lines) == 120                     # 4초 × 30fps
    last = json.loads(lines[-1])
    assert set(last) == {"frame", "speed_kmh", "distance_m", "ttc_s", "level"}
    assert last["level"] == "위험"                    # 마지막엔 10m 남짓까지 접근
