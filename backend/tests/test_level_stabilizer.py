from app.judgment.level_stabilizer import LevelStabilizer


def run(levels, hold_frames=3):
    st = LevelStabilizer(hold_frames)
    return [st.update(lv) for lv in levels]


def test_raise_is_immediate():
    assert run(["정상", "위험"]) == ["정상", "위험"]


def test_lower_waits_for_hold_frames():
    out = run(["경고", "정상", "정상", "정상"])
    assert out == ["경고", "경고", "경고", "정상"]   # 3프레임 연속 정상일 때 내려감


def test_flicker_is_suppressed():
    # 경고와 정상이 번갈아 나와도 화면은 경고 유지
    out = run(["경고", "정상", "경고", "정상", "경고", "정상"])
    assert out == ["경고"] * 6


def test_reset_clears_state():
    st = LevelStabilizer(3)
    st.update("위험")
    st.reset()
    assert st.update("정상") == "정상"
