from app.config import load_config
from app.judgment.judge import FrameJudge
from test_fake_input import FPS, load

F_PX = 1000   # make_fake_input.py와 같은 가짜 초점거리


def make_judge():
    cfg = load_config()   # 실제 backend/config.yaml 값을 그대로 사용
    return FrameJudge(cfg["judgment"], fps=FPS, focal_px=F_PX)


def test_output_has_interface_keys():
    out = make_judge().judge_frame(load("approach")[0], speed_kmh=100)
    assert set(out) == {"frame", "speed_kmh", "distance_m", "ttc_s", "level"}


def test_approach_reaches_warning_then_danger():
    # 접근 장면: 정답 TTC = 5 - t초 → t=2초(60프레임)에 3초, t=3.5초(105프레임)에 1.5초
    judge = make_judge()
    outs = [judge.judge_frame(row, speed_kmh=None) for row in load("approach")]
    assert outs[50]["level"] == "정상"
    assert outs[70]["level"] == "경고"
    assert outs[110]["level"] == "위험"


def test_lead_change_resets_ttc():
    judge = make_judge()
    rows = load("approach")
    for row in rows[:40]:
        judge.judge_frame(row, speed_kmh=None)
    switched = dict(rows[40], lead=dict(rows[40]["lead"], id=2))   # 앞차 ID만 바꿈
    out = judge.judge_frame(switched, speed_kmh=None)
    assert out["ttc_s"] is None   # 새 앞차는 프레임이 모일 때까지 TTC 없음


def test_no_lead_is_normal():
    judge = make_judge()
    out = judge.judge_frame(dict(load("approach")[0], lead=None), speed_kmh=100)
    assert out["distance_m"] is None and out["level"] == "정상"
