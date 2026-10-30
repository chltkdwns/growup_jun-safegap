"""영상 하나에 A(인식)를 돌려 JSON과 디버그 영상을 저장한다.

실행 (backend 폴더에서):
    python -m scripts.run_perception --video data/dev/sample.mp4
결과:
    outputs/sample_perception.json, outputs/sample_debug.mp4
"""

import argparse
import json
from pathlib import Path

import yaml

from app.perception.pipeline import analyze_video


def main() -> None:
    """명령줄 인자를 읽어 analyze_video()를 실행하고 결과를 파일로 저장한다.

    사용처: 개발 중 A 혼자 결과를 눈으로 확인할 때 직접 실행한다.
    입력: --video 영상 경로, --config 설정 파일 경로 (기본 config.yaml)
    출력: output_dir에 JSON과 디버그 영상
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    output_dir = Path(cfg["paths"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(args.video).stem

    results = analyze_video(
        args.video,
        cfg["paths"]["yolo_weights"],
        cfg["perception"],
        debug_video_path=str(output_dir / f"{stem}_debug.mp4"),
    )

    json_path = output_dir / f"{stem}_perception.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([r.model_dump() for r in results], f, ensure_ascii=False, indent=1)

    lead_frames = sum(r.lead is not None for r in results)
    cut_in_frames = sum(r.cut_in for r in results)
    print(f"프레임 {len(results)}개, 앞차 있음 {lead_frames}, 끼어들기 {cut_in_frames}")
    print(f"저장: {json_path}")


if __name__ == "__main__":
    main()
