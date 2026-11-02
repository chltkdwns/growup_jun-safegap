"""KITTI tracking 시퀀스 하나를 B로 판단하고, 핀홀 거리를 정답 거리와 비교한다.

사용처: B(판단) 로직을 실제 장면으로 검증할 때. 결과 JSONL은 C의 mock API에도 쓸 수 있다.
실행 예 (backend 폴더에서):
    python tools/run_kitti_judge.py 0000
"""
import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))  # backend를 import 경로에 추가

from app.config import load_config  # noqa: E402
from app.data_sources.kitti import labels_to_ab, read_focal_px, read_speeds_kmh  # noqa: E402
from app.judgment.judge import FrameJudge  # noqa: E402


def judge_sequence(root: Path, seq: str, cfg: dict) -> tuple[list[dict], list[float | None]]:
    """KITTI 시퀀스 하나의 B→C 결과와 프레임별 정답 거리를 돌려준다.

    사용처: 이 스크립트의 main()과 test_run_kitti_judge.py에서 호출한다.
    입력: root KITTI training 폴더, seq 시퀀스 번호("0000"), cfg 전체 설정
    출력: (B→C 결과 목록, 정답 거리 목록[m])
    """
    speeds = read_speeds_kmh(root / "oxts" / f"{seq}.txt")
    rows, truth = labels_to_ab(
        root / "label_02" / f"{seq}.txt", len(speeds),
        cfg["kitti"]["lane_half_width_m"], cfg["kitti"]["fps"],
    )
    judge = FrameJudge(cfg["judgment"], fps=cfg["kitti"]["fps"], focal_px=read_focal_px(root / "calib" / f"{seq}.txt"))
    results = [judge.judge_frame(row, speeds[i]) for i, row in enumerate(rows)]
    return results, truth


def distance_errors_pct(results: list[dict], truth: list[float | None]) -> list[float]:
    """앞차가 있는 프레임마다 핀홀 거리의 오차율(%)을 구한다. (+면 실제보다 멀게 추정)"""
    return [
        (r["distance_m"] - t) / t * 100
        for r, t in zip(results, truth)
        if r["distance_m"] is not None and t is not None
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="KITTI 시퀀스로 B 판단 결과 생성 및 거리 오차 측정")
    parser.add_argument("seq", help="시퀀스 번호, 예: 0000")
    args = parser.parse_args()

    cfg = load_config()
    root = BACKEND / cfg["kitti"]["root"]
    results, truth = judge_sequence(root, args.seq, cfg)

    out = BACKEND / cfg["paths"]["output_dir"] / f"kitti_{args.seq}_judged.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results), encoding="utf-8")

    errs = distance_errors_pct(results, truth)
    levels = [r["level"] for r in results]
    print(f"saved {out} ({len(results)} frames)")
    print(f"앞차가 있는 프레임: {len(errs)} / {len(results)}")
    if errs:
        mean_abs = sum(abs(e) for e in errs) / len(errs)
        print(f"핀홀 거리 오차: 평균 |오차| {mean_abs:.1f}%, 최소 {min(errs):+.1f}%, 최대 {max(errs):+.1f}%")
    print("경고 단계 프레임 수:", {lv: levels.count(lv) for lv in ["정상", "주의", "경고", "위험"]})


if __name__ == "__main__":
    main()
