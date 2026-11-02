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
    """다른 차로 바뀜(id도 다르고 박스도 안 겹침) → TTC 리셋"""
    judge = make_judge()
    rows = load("approach")
    for row in rows[:40]:
        judge.judge_frame(row, speed_kmh=None)
    x1, y1, x2, y2 = rows[40]["lead"]["box"]
    switched = dict(rows[40], lead={"id": 2, "box": [x1 + 500, y1, x2 + 500, y2]})
    assert judge.judge_frame(switched, speed_kmh=None)["ttc_s"] is None


def test_id_switch_same_box_keeps_ttc():
    """같은 차인데 id만 바뀜(박스 그대로) → TTC 유지"""
    judge = make_judge()
    rows = load("approach")
    for row in rows[:40]:
        judge.judge_frame(row, speed_kmh=None)
    switched = dict(rows[40], lead=dict(rows[40]["lead"], id=2))
    assert judge.judge_frame(switched, speed_kmh=None)["ttc_s"] is not None

def test_no_lead_is_normal():
    judge = make_judge()
    out = judge.judge_frame(dict(load("approach")[0], lead=None), speed_kmh=100)
    assert out["distance_m"] is None and out["level"] == "정상"


def test_short_miss_keeps_last_result():
    """앞차를 1프레임 놓침 → 직전 결과 유지, 다시 잡히면 TTC 이어짐"""
    judge = make_judge()
    rows = load("approach")
    outs = [judge.judge_frame(row, speed_kmh=None) for row in rows[:40]]
    missed = judge.judge_frame(dict(rows[40], lead=None), speed_kmh=None)
    assert missed["ttc_s"] == outs[-1]["ttc_s"] and missed["level"] == outs[-1]["level"]
    assert judge.judge_frame(rows[41], speed_kmh=None)["ttc_s"] is not None


def test_long_miss_resets():
    """max_missing_s보다 오래 놓침 → 앞차 없음(정상)으로 처리"""
    judge = make_judge()
    rows = load("approach")
    for row in rows[:40]:
        judge.judge_frame(row, speed_kmh=None)
    n = round(load_config()["judgment"]["max_missing_s"] * FPS)
    outs = [judge.judge_frame(dict(rows[40 + i], lead=None), speed_kmh=None) for i in range(n + 1)]
    assert outs[-1]["distance_m"] is None and outs[-1]["level"] == "정상"