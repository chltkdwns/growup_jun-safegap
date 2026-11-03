import pytest

from app.judgment.warning_level import decide_event

HARD = 10.0  # config의 hard_brake_rel_mps와 같은 값


@pytest.mark.parametrize(
    "level, cut_in, rel_speed_mps, expected",
    [
        ("정상", True, 20.0, None),          # 정상이면 이유 없음 (끼어들기여도)
        ("경고", True, 20.0, "cut_in"),      # 겹치면 끼어들기가 먼저
        ("위험", False, 10.0, "hard_brake"), # 경계값: 10m/s 이상이면 급정거
        ("위험", False, 9.99, "gap_short"),  # 10m/s 미만이면 안전거리 부족
        ("주의", False, 0.0, "gap_short"),
    ],
)
def test_event(level, cut_in, rel_speed_mps, expected):
    assert decide_event(level, cut_in, rel_speed_mps, HARD) == expected