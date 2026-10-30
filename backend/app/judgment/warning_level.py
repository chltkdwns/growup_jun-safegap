KMH_TO_MS = 1 / 3.6                       # km/h → m/s 변환
LEVELS = ["정상", "주의", "경고", "위험"]  # 경고 단계, 뒤로 갈수록 위험


def safe_distance_m(speed_kmh: float, safe_gap_s: float) -> float:
    """내 속도로 safe_gap_s초 동안 가는 거리(안전거리, m)를 구한다.

    사용처: B(판단) 단계. decide_level()이 안전거리 부족 여부를 판단할 때 호출한다.
    입력: speed_kmh 내 속도(km/h), safe_gap_s 안전거리 기준 시간(초, config)
    출력: 안전거리(m). 예: 100km/h, 2초 → 약 55.6m
    """
    return speed_kmh * KMH_TO_MS * safe_gap_s


def decide_level(
    distance_m: float | None,
    speed_kmh: float | None,
    ttc_s: float | None,
    cut_in: bool,
    safe_gap_s: float,
    ttc_warning_s: float,
    ttc_danger_s: float,
) -> str:
    """거리, 속도, TTC, 끼어들기로 한 프레임의 경고 단계를 정한다.

    사용처: B(판단) 단계. 매 프레임 거리·TTC 계산 뒤에 호출하고, 결과를 B→C JSON의 level에 넣는다.
    입력: distance_m 앞차 거리(m), speed_kmh 내 속도(km/h), ttc_s TTC(초),
          cut_in 끼어들기 여부, 나머지는 config의 판단 기준
    출력: "정상" / "주의" / "경고" / "위험"
    주의: 앞차가 없거나 속도를 모르면 해당 값은 None으로 넘기고, 그 기준은 건너뛴다.
    """
    # 1) TTC 기준이 가장 우선 (이하면 해당 단계)
    if ttc_s is not None and ttc_s <= ttc_danger_s:
        level = 3
    elif ttc_s is not None and ttc_s <= ttc_warning_s:
        level = 2
    # 2) TTC가 여유 있어도 안전거리가 부족하면 주의
    elif (
        distance_m is not None
        and speed_kmh is not None
        and distance_m < safe_distance_m(speed_kmh, safe_gap_s)
    ):
        level = 1
    else:
        level = 0
    # 3) 끼어들기가 있으면 한 단계 올림 (최대 "위험")
    if cut_in:
        level = min(level + 1, len(LEVELS) - 1)
    return LEVELS[level]
