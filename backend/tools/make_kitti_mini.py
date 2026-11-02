"""테스트용 가짜 KITTI 형식 파일을 tests/fixtures/kitti_mini에 만든다. (실제 KITTI 데이터 아님)"""
from pathlib import Path

base = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "kitti_mini"
for sub in ["calib", "oxts", "label_02"]:
    (base / sub).mkdir(parents=True, exist_ok=True)

fx = 700.0   # 가짜 초점거리(px)
(base / "calib/0000.txt").write_text(
    f"P0: {fx} 0 600 0 0 {fx} 170 0 0 0 1 0\nP2: {fx} 0 600 45 0 {fx} 170 0 0 0 1 0\n"
)
# 10프레임, 내 전방 속도 vf = 20 m/s (= 72km/h)
(base / "oxts/0000.txt").write_text("49 8 100 0 0 0 0 0 20.0 0 0\n" * 10)

lines = []
for fr in range(10):
    rear = 30 - fr * 1.0                    # 앞차 뒷면: 30m에서 프레임마다 1m씩 가까워짐
    z = rear + 4.2 / 2                      # KITTI의 z는 차 중심 = 뒷면 + 길이(4.2m)/2
    w_px = fx * 1.8 / rear                  # 카메라에 보이는 뒷면 폭(1.8m)의 박스 폭
    left, right = 600 - w_px / 2, 600 + w_px / 2
    lines.append(f"{fr} 3 Car 0 0 0 {left:.2f} 150 {right:.2f} 200 1.5 1.8 4.2 0.2 1.6 {z:.2f} 0")
    lines.append(f"{fr} 5 Car 0 0 0 100 150 160 200 1.5 1.8 4.2 -5.0 1.6 {z - 10:.2f} 0")  # 옆 차선 차
    lines.append(f"{fr} -1 DontCare -1 -1 -10 0 0 10 10 -1 -1 -1 -1000 -1000 -1000 -10")
(base / "label_02/0000.txt").write_text("\n".join(lines) + "\n")
print("saved", base)