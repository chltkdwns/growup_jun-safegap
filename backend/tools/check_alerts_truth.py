"""
요약: KITTI 정답 거리로 계산한 경고 단계와, B가 추정한 경고 단계를 프레임별로 비교한다.
사용처: B 판단 결과 검증용 (backend에서 python -m tools.check_alerts_truth)
입력: data/kitti/training (label_02, image_02), outputs/kitti_0000_judged.jsonl
출력: 화면에 프레임 / 정답 거리·TTC·단계 / 추정 거리·TTC·단계 출력
주의: 정답 TTC는 0.5초 전 거리와 비교해서 구하므로, 앞차가 바뀌는 구간에서는 틀린 값이 나온다.
      run_kitti_judge.py를 먼저 실행해야 jsonl 파일이 생긴다.
"""

import json
from pathlib import Path
from app.config import load_config
from app.data_sources.kitti import labels_to_ab
from app.judgment.warning_level import decide_level

cfg = load_config()
k, j = cfg["kitti"], cfg["judgment"]
root = Path(k["root"])
n = len(list((root / "image_02" / "0000").glob("*.png")))
_, truth = labels_to_ab(root / "label_02" / "0000.txt", n, k["lane_half_width_m"], k["fps"])

est = {r["frame"]: r for r in map(json.loads, open("outputs/kitti_0000_judged.jsonl", encoding="utf-8"))}
gap = 5  # 0.5초 전 거리와 비교
for f in range(125, 145):
    d, d_old = truth[f], truth[f - gap]
    if d is None or d_old is None:
        continue
    closing = (d_old - d) / (gap / k["fps"])          # 다가오는 속도(m/s)
    ttc = d / closing if closing > 0 else None
    lv = decide_level(d, est[f]["speed_kmh"], ttc, False, j["safe_gap_s"], j["ttc_warning_s"], j["ttc_danger_s"])
    print(f, "정답", round(d, 1), ttc and round(ttc, 2), lv, "| 추정", est[f]["distance_m"], est[f]["ttc_s"], est[f]["level"])