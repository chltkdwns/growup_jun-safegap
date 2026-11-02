"""A→B JSONL 파일을 읽어 B→C JSONL 파일로 저장한다.

사용처: A의 실제 출력이 나오기 전, C가 mock API와 React 화면에서 쓸 판단 결과를 만들 때.
실행 예 (backend 폴더에서):
    python tools/run_judge.py tests/fixtures/fake_approach.jsonl outputs/judged_approach.jsonl --speed-kmh 100 --focal-px 1000
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # backend를 import 경로에 추가

from app.config import load_config  # noqa: E402
from app.judgment.judge import FrameJudge  # noqa: E402


def judge_file(in_path: Path, out_path: Path, judge: FrameJudge, speed_kmh: float | None) -> int:
    """A→B JSONL을 한 줄씩 판단해 B→C JSONL로 저장하고, 처리한 프레임 수를 돌려준다.

    사용처: 이 스크립트의 main()과 test_run_judge.py에서 호출한다.
    입력: in_path A→B JSONL 경로, out_path 저장할 경로, judge 영상 하나용 FrameJudge,
          speed_kmh 내 속도(km/h, 모르면 None. 지금은 영상 전체에 같은 값을 씀)
    출력: 처리한 프레임 수
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(in_path, encoding="utf-8") as fin, open(out_path, "w", encoding="utf-8") as fout:
        for line in fin:
            result = judge.judge_frame(json.loads(line), speed_kmh)   # 한 프레임 판단
            fout.write(json.dumps(result, ensure_ascii=False) + "\n")  # 한글 level을 그대로 저장
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="A→B JSONL을 B→C JSONL로 변환")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--speed-kmh", type=float, default=None)
    parser.add_argument("--focal-px", type=float, default=None, help="없으면 config의 camera.focal_px 사용")
    args = parser.parse_args()

    cfg = load_config()
    focal_px = args.focal_px or cfg["camera"]["focal_px"]
    if focal_px is None:
        sys.exit("초점거리가 없어요. --focal-px를 주거나 config.yaml의 camera.focal_px를 채워 주세요.")

    judge = FrameJudge(cfg["judgment"], fps=args.fps, focal_px=focal_px)
    n = judge_file(args.input, args.output, judge, args.speed_kmh)
    print(f"saved {args.output} ({n} frames)")


if __name__ == "__main__":
    main()
