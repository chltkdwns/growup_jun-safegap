# tests/test_level_stabilizer.py 전체 교체
from app.judgment.level_stabilizer import LevelStabilizer

STEP_S = 0.1  # 테스트용 프레임 간격(초)


def run(levels, hold_s=0.2, times=None):
    st = LevelStabilizer(hold_s)
    times = times or [i * STEP_S for i in range(len(levels))]
    return [st.update(lv, t) for lv, t in zip(levels, times)]


def test_raise_is_immediate():
    assert run(["정상", "위험"]) == ["정상", "위험"]


def test_lower_waits_for_hold_s():
    out = run(["경고", "정상", "정상", "정상"])
    assert out == ["경고", "경고", "경고", "정상"]   # 정상이 0.2초 이어진 프레임(0.3초)에 내려감


def test_lower_uses_time_not_frame_count():
    # 프레임 간격이 벌어지면 정상 두 번째 프레임에서 이미 0.3초가 지나 바로 내려감
    out = run(["경고", "정상", "정상"], times=[0.0, 0.1, 0.4])
    assert out == ["경고", "경고", "정상"]


def test_flicker_is_suppressed():
    out = run(["경고", "정상", "경고", "정상", "경고", "정상"])
    assert out == ["경고"] * 6


def test_reset_clears_state():
    st = LevelStabilizer(0.2)
    st.update("위험", 0.0)
    st.reset()
    assert st.update("정상", 0.1) == "정상"