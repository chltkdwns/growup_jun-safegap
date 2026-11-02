import pytest

from app.judgment.warning_level import decide_level, safe_distance_m

# config.yaml의 judgment 기준과 같은 값
CFG = dict(safe_gap_s=2.0, ttc_warning_s=3.0, ttc_danger_s=1.5)


def test_safe_distance_100kmh_is_about_55m():
    assert safe_distance_m(100, 2.0) == pytest.approx(55.56, abs=0.01)


@pytest.mark.parametrize(
    "ttc_s, expected",
    [
        (3.01, "정상"),  # 경고 기준 바로 위
        (3.0, "경고"),   # 정확히 3초: "이하"라서 경고
        (1.51, "경고"),
        (1.5, "위험"),   # 정확히 1.5초: "이하"라서 위험
        (None, "정상"),  # 가까워지지 않음
    ],
)
def test_ttc_boundaries(ttc_s, expected):
    # 거리는 충분히 멀게 두고 TTC만 확인
    assert decide_level(100, 100, ttc_s, False, **CFG) == expected


def test_safe_distance_shortage_is_caution():
    # 100km/h에서 안전거리 약 55.6m → 50m면 부족
    assert decide_level(50, 100, None, False, **CFG) == "주의"
    assert decide_level(60, 100, None, False, **CFG) == "정상"


def test_unknown_speed_skips_safe_distance():
    assert decide_level(10, None, None, False, **CFG) == "정상"


def test_cut_in_raises_one_level_up_to_danger():
    assert decide_level(100, 100, None, True, **CFG) == "주의"   # 정상 → 주의
    assert decide_level(100, 100, 2.0, True, **CFG) == "위험"   # 경고 → 위험
    assert decide_level(100, 100, 1.0, True, **CFG) == "위험"   # 위험은 그대로
