"""KITTI 시퀀스에서 핀홀 거리 오차가 큰 앞차를 찾아 원인을 같이 출력한다. (분석용 일회성 스크립트)"""
import math
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.config import load_config  # noqa: E402
from app.data_sources.kitti import VEHICLE_TYPES, read_focal_px  # noqa: E402

seq = sys.argv[1]
cfg = load_config()
root = BACKEND / cfg["kitti"]["root"]
focal_px = read_focal_px(root / "calib" / f"{seq}.txt")
car_w_m = cfg["judgment"]["car_width_m"]
half_w = cfg["kitti"]["lane_half_width_m"]

# 1) 프레임별로 내 차선의 가장 가까운 차(앞차)만 고르기 (kitti.py와 같은 규칙)
leads = {}
for line in (root / "label_02" / f"{seq}.txt").read_text().splitlines():
    f = line.split()
    if len(f) < 17 or f[2] not in VEHICLE_TYPES:
        continue
    x, z = float(f[13]), float(f[15])
    if abs(x) <= half_w and z > 0 and (int(f[0]) not in leads or z < float(leads[int(f[0])][15])):
        leads[int(f[0])] = f

# 2) 앞차마다 추정 거리, 정답(뒷면) 거리, 오차와 원인 후보 계산
rows = []
for frame, f in sorted(leads.items()):
    box_w = float(f[8]) - float(f[6])
    est = focal_px * car_w_m / box_w
    truth = float(f[15]) - float(f[12]) / 2
    # 차가 정면 뒷모습에서 얼마나 틀어져 있는지(도): 0이면 뒷모습이 정면으로 보임
    view_deg = math.degrees(abs(math.atan2(math.sin(float(f[5]) + math.pi / 2),
                                           math.cos(float(f[5]) + math.pi / 2))))
    rows.append((frame, int(f[1]), f[2], est, truth, (est - truth) / truth * 100,
                 float(f[11]), view_deg, float(f[3]), int(f[4]), float(f[6]), float(f[8])))

print(f"앞차 프레임 {len(rows)}개, 초점거리 {focal_px:.1f}px")
print("frame  id  종류    추정(m) 정답(m)  오차%  실제폭  틀어짐(도) 잘림 가려짐  박스 x1~x2")
for r in sorted(rows, key=lambda r: r[5])[:10]:   # 오차가 가장 큰(가장 마이너스) 10개
    print(f"{r[0]:5d} {r[1]:3d}  {r[2]:6s} {r[3]:7.1f} {r[4]:7.1f} {r[5]:6.1f}  {r[6]:5.2f}  {r[7]:8.1f}  "
          f"{r[8]:4.1f} {r[9]:5d}   {r[10]:6.0f}~{r[11]:.0f}")


for name, keep in [("뒷면(≤20°)", lambda r: r[7] <= 20), ("비스듬(>20°)", lambda r: r[7] > 20)]:
    g = [abs(r[5]) for r in rows if keep(r)]
    if g:
        print(f"{name}: {len(g)}프레임, 평균 |오차| {sum(g)/len(g):.1f}%")

print("\n뒷면 그룹(각도 작은 순)")
for r in sorted([r for r in rows if r[7] <= 20], key=lambda r: r[7])[:10]:
    print(f"{r[0]:5d} {r[1]:3d} {r[2]:5s} 추정 {r[3]:5.1f} 정답 {r[4]:5.1f} 오차 {r[5]:6.1f}% 각도 {r[7]:5.1f} 가려짐 {r[9]}")