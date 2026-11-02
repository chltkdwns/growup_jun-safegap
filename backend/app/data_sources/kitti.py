from pathlib import Path

MS_TO_KMH = 3.6
OXTS_VF_INDEX = 8                     # oxts 한 줄에서 전방 속도 vf(m/s)의 위치 (vn, ve와 크기가 일치해 확인함)
VEHICLE_TYPES = {"Car", "Van", "Truck"}  # 앞차 후보로 볼 KITTI 클래스


def read_focal_px(calib_path: Path) -> float:
    """KITTI calib 파일에서 왼쪽 컬러 카메라(P2)의 초점거리 fx(px)를 읽는다.

    사용처: B(판단) 단계. KITTI 시퀀스를 처리하기 전 한 번 호출해 FrameJudge의 focal_px로 쓴다.
    입력: calib_path training/calib/0000.txt 같은 파일 경로
    출력: 초점거리(px). 예: 721.5377
    """
    for line in Path(calib_path).read_text().splitlines():
        if line.startswith("P2:"):
            return float(line.split()[1])   # P2 행렬의 첫 값이 fx
    raise ValueError(f"P2 행이 없어요: {calib_path}")


def read_speeds_kmh(oxts_path: Path) -> list[float]:
    """KITTI tracking oxts 파일에서 프레임별 내 속도(km/h)를 읽는다.

    사용처: B(판단) 단계. 프레임 번호를 인덱스로 써서 judge_frame()의 speed_kmh로 넘긴다.
    입력: oxts_path training/oxts/0000.txt 같은 파일 경로 (한 줄 = 한 프레임)
    출력: 프레임 순서의 속도 목록(km/h)
    """
    lines = Path(oxts_path).read_text().splitlines()
    return [float(line.split()[OXTS_VF_INDEX]) * MS_TO_KMH for line in lines if line.strip()]


def labels_to_ab(label_path: Path, n_frames: int, lane_half_width_m: float, fps: float):
    """KITTI 정답 라벨로 A→B 형식의 프레임 목록과 정답 거리 목록을 만든다.

    사용처: A의 실제 출력이 나오기 전, B를 실제 장면으로 검증할 때 tools/run_kitti_judge.py가 호출한다.
    입력: label_path training/label_02/0000.txt, n_frames 시퀀스 프레임 수(oxts 줄 수),
          lane_half_width_m 내 차선으로 볼 좌우 폭의 절반(m, config), fps 프레임 속도
    출력: (A→B 행 목록, 프레임별 정답 거리 목록[m, 앞차 없으면 None])
    주의: 앞차는 정답 3D 위치로 고른다(가로 위치 |x| ≤ lane_half_width_m 중 가장 가까운 차).
          A의 실제 앞차 선정과 다르므로, B의 거리·TTC 계산만 검증하는 용도다.
    """
    # 1) 프레임별로 차량 라벨만 모으기
    by_frame: dict[int, list[list[str]]] = {}
    for line in Path(label_path).read_text().splitlines():
        f = line.split()
        if len(f) < 17 or f[2] not in VEHICLE_TYPES:
            continue                                   # DontCare, 사람, 자전거 등은 제외
        by_frame.setdefault(int(f[0]), []).append(f)

    rows, truth = [], []
    for frame in range(n_frames):
        # 2) 내 차선 안(|x| 작음)이고 앞에 있는(z > 0) 차 중 가장 가까운 차를 앞차로
        in_lane = [
            f for f in by_frame.get(frame, [])
            if abs(float(f[13])) <= lane_half_width_m and float(f[15]) > 0
        ]
        lead = min(in_lane, key=lambda f: float(f[15]), default=None)
        rows.append({
            "frame": frame,
            "time": round(frame / fps, 4),
            "lead": None if lead is None else {
                "id": int(lead[1]),
                "box": [float(v) for v in lead[6:10]],   # left, top, right, bottom (px)
            },
            "cut_in": False,                              # 정답 라벨에는 끼어들기 정보가 없음
        })
        truth.append(None if lead is None else float(lead[15]) - float(lead[12]) / 2)   # z = 카메라 앞쪽 거리(m)
    return rows, truth
