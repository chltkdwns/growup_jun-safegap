"""영상 하나에 A(인식) → B(판단)를 차례로 돌려 합친 결과를 outputs/{video_id}.json으로 저장한다.

실행 (backend 폴더에서):
    python -m scripts.analyze_and_judge --video data/dev/sample.mp4 --speed-kmh 60 --hfov-deg 110
카메라마다 다른 값(본넷 비율 등)은 --camera로 덮어쓴다:
    python -m scripts.analyze_and_judge --video data/dev/sample.mp4 --camera configs/finevu_lx3000.yaml ...
결과: outputs/sample.json (프레임별 인식 + 판단 결과를 합친 리스트, 재생 모드가 읽는다)
"""

import argparse
import json
import sys
from pathlib import Path

import cv2
import yaml

from app.config import load_config
from app.judgment.distance import focal_px_from_hfov
from app.judgment.judge import FrameJudge
from app.perception.pipeline import analyze_video


def judge_frames(
    perceptions: list[dict], judge: FrameJudge, speed_kmh: float | None
) -> list[dict]:
    """A의 프레임별 인식 결과에 B 판단을 붙여 한 프레임당 dict 하나로 합친다.

    사용처: 이 스크립트의 main()이 analyze_video() 직후 호출한다.
    입력: perceptions PerceptionFrame을 dict로 바꾼 리스트, judge 영상 하나용 FrameJudge,
          speed_kmh 내 속도(km/h, 영상 전체에 같은 값. 모르면 None)
    출력: {"frame", "time", "lead", "cut_in", "speed_kmh", "distance_m", "ttc_s", "level"} 리스트
    주의: 프레임 순서대로 호출해야 한다 (TTC가 이전 프레임을 쓴다).
    """
    merged = []
    for p in perceptions:
        j = judge.judge_frame(p, speed_kmh)
        # 인식 결과(lead, cut_in, time)와 판단 결과를 한 줄로 합친다. frame은 둘이 같다
        merged.append({**p, **j})
    return merged


def main() -> None:
    """명령줄 인자를 읽어 인식 → 판단을 돌리고 합친 JSON을 저장한다.

    사용처: 재생 모드용 결과 파일을 만들 때 직접 실행한다.
    입력: --video 영상, --config 설정(기본 config.yaml), --camera 카메라별 덮어쓰기 설정,
          --speed-kmh 내 속도, --focal-px 또는 --hfov-deg (없으면 config.camera 값)
    출력: 없음. outputs/{영상 이름}.json 저장, 단계별 프레임 수 출력
    """
    parser = argparse.ArgumentParser(description="인식 → 판단을 돌려 합친 JSON 저장")
    parser.add_argument("--video", required=True)
    parser.add_argument("--config", default=None)
    parser.add_argument("--camera", default=None)
    parser.add_argument("--speed-kmh", type=float, default=None)
    parser.add_argument("--focal-px", type=float, default=None)
    parser.add_argument("--hfov-deg", type=float, default=None)
    args = parser.parse_args()

    cfg = load_config(Path(args.config)) if args.config else load_config()
    if args.camera is not None:
        with open(args.camera, encoding="utf-8") as f:
            cfg["perception"].update(yaml.safe_load(f))

    # 1단계: 초점거리 정하기 (인자 → config focal_px → hfov로 계산 순서)
    cap = cv2.VideoCapture(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_w_px = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    cap.release()
    hfov_deg = args.hfov_deg or cfg["camera"]["hfov_deg"]
    focal_px = args.focal_px or cfg["camera"]["focal_px"]
    if focal_px is None and hfov_deg is not None:
        focal_px = focal_px_from_hfov(frame_w_px, hfov_deg)
    if focal_px is None:
        sys.exit("초점거리가 없어요. --focal-px나 --hfov-deg를 주거나 config.yaml의 camera를 채워 주세요.")

    # 2단계: A(인식) → B(판단) 순서로 돌려 합친다
    perceptions = [
        r.model_dump()
        for r in analyze_video(args.video, cfg["perception"]["model"], cfg["perception"])
    ]
    judge = FrameJudge(cfg["judgment"], fps=fps, focal_px=focal_px)
    merged = judge_frames(perceptions, judge, args.speed_kmh)

    # 3단계: 저장
    output_dir = Path(cfg["paths"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{Path(args.video).stem}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=1)

    levels = {}
    for m in merged:
        levels[m["level"]] = levels.get(m["level"], 0) + 1
    print(f"프레임 {len(merged)}개, focal_px {focal_px:.1f}, 단계별 {levels}")
    print(f"저장: {out_path}")


if __name__ == "__main__":
    main()
