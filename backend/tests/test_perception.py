"""A(인식) 단위 테스트. YOLO 없이 가짜 박스로 앞차 선정과 끼어들기를 확인한다.

실행 (backend 폴더에서): python -m pytest tests
"""

from app.perception.cut_in import CutInDetector
from app.perception.lateral import lateral_offset_m
from app.perception.lead import select_lead
from app.perception.pipeline import perceive_frame

FRAME_W_PX = 1000
CENTER_X_PX = 500  # 정면은 화면 중앙
CAR_W_M = 1.8
LANE_HALF_M = 1.7
ZONE_M = 2.0
MOVE_M = 0.3
MIN_BOX_W_PX = 40


def box_at(center_x: float, width: float = 100) -> list[float]:
    """가운데 x가 center_x이고 정사각형인 테스트용 박스 (아래쪽 y=800)."""
    return [center_x - width / 2, 800 - width, center_x + width / 2, 800]


def make_detector(approach_frames: int) -> CutInDetector:
    """차선 반폭 1.7m, 바깥 2m 안에서 0.3m 이상 다가와야 끼어들기로 보는 테스트용 판단기."""
    return CutInDetector(approach_frames, CAR_W_M, LANE_HALF_M, ZONE_M, MOVE_M, MIN_BOX_W_PX)


def run(detector: CutInDetector, boxes: list[list[float]]) -> list[bool]:
    """같은 차(ID 1)의 박스를 프레임 순서대로 넣고 프레임별 결과를 돌려준다."""
    return [detector.update({1: b}, CENTER_X_PX, FRAME_W_PX) for b in boxes]


def test_lateral_offset_uses_box_width_as_scale():
    # 폭 100px 박스가 정면에서 100px 오른쪽 → 차폭 1.8m 기준 1.8m
    assert lateral_offset_m(box_at(600, 100), CENTER_X_PX, CAR_W_M) == 1.8
    # 같은 100px 왼쪽이라도 폭이 200px(더 가까움)이면 0.9m, 부호는 왼쪽이 음수
    assert lateral_offset_m(box_at(400, 200), CENTER_X_PX, CAR_W_M) == -0.9


def test_lead_is_largest_box_inside():
    tracks = {
        1: box_at(500, 80),  # 안, 멀리
        2: box_at(520, 200),  # 안, 가까이 → 앞차
        3: box_at(100, 300),  # 바깥(-2.4m), 제일 큼
    }
    assert select_lead(tracks, CENTER_X_PX, CAR_W_M, LANE_HALF_M) == 2


def test_no_lead_when_all_outside():
    assert select_lead({1: box_at(100)}, CENTER_X_PX, CAR_W_M, LANE_HALF_M) is None


def test_lead_boundary_is_inclusive():
    # 폭 100px에서 1.7m는 94.44px. 94px(1.692m)는 안, 95px(1.71m)는 밖
    assert select_lead({1: box_at(594)}, CENTER_X_PX, CAR_W_M, LANE_HALF_M) == 1
    assert select_lead({1: box_at(595)}, CENTER_X_PX, CAR_W_M, LANE_HALF_M) is None


def test_cut_in_when_crossing_boundary():
    # 3.6m(바깥) → 1.62m(안): 같은 쪽에서 경계를 넘어 들어옴
    assert run(make_detector(5), [box_at(700), box_at(590)]) == [False, True]


def test_no_cut_in_when_jumping_to_other_side():
    # 오른쪽 바깥에서 왼쪽 안으로 건너뛰는 것은 같은 차의 이동이 아니라 측정 오류로 본다
    assert run(make_detector(5), [box_at(700), box_at(410)]) == [False, False]


def test_cut_in_after_n_approach_frames():
    # 2.52 → 2.34 → 2.16 → 1.98m: N=3프레임 동안 0.54m 안쪽으로 다가옴
    flags = run(make_detector(3), [box_at(x) for x in (640, 630, 620, 610)])
    assert flags == [False, False, False, True]


def test_no_cut_in_for_slow_drift():
    # 4프레임 동안 0.054m만 다가오는 움직임은 move_m(0.3m)에 못 미친다
    flags = run(make_detector(3), [box_at(x) for x in (640, 639, 638, 637)])
    assert flags == [False] * 4


def test_no_cut_in_for_car_outside_zone():
    # 차선에서 2m보다 더 먼 곳(4.5m)에서 다가오는 차는 후보가 아니다
    flags = run(make_detector(3), [box_at(x) for x in (750, 740, 730, 720)])
    assert flags == [False] * 4


def test_no_cut_in_for_small_far_box():
    # 폭 30px(최소 40px 미만)인 작은 박스는 같은 움직임이어도 판단하지 않는다
    small = [box_at(x, 30) for x in (550, 547, 544, 541)]
    assert run(make_detector(3), small) == [False] * 4
    # 폭 50px이면 8px 이동이 0.3m 이상이라 끼어들기로 본다
    normal = [box_at(x, 50) for x in (560, 556, 552, 548)]
    assert run(make_detector(3), normal)[-1] is True


def test_no_cut_in_for_box_clipped_at_frame_edge():
    # 오른쪽 끝(x2=1000)에 닿은 박스는 폭이 잘려서 판단하지 않는다
    clipped = [[1000 - w, 700, 1000, 800] for w in (200, 240, 280, 320)]
    assert run(make_detector(3), clipped) == [False] * 4
    # 같은 움직임이라도 화면 끝에 안 닿으면 끼어들기로 본다
    inside = [[999 - w, 700, 999, 800] for w in (200, 240, 280, 320)]
    assert run(make_detector(3), inside)[-1] is True


def test_no_cut_in_for_car_already_inside_or_moving_away():
    detector = make_detector(2)
    for x in [650, 660, 670]:  # 바깥에서 멀어짐
        tracks = {1: box_at(x), 2: box_at(500)}
        assert detector.update(tracks, CENTER_X_PX, FRAME_W_PX) is False


def test_perceive_frame_matches_interface():
    detector = make_detector(5)
    result = perceive_frame(
        {3: box_at(500)},
        frame_idx=120,
        fps=30.0,
        center_x_px=CENTER_X_PX,
        cut_in_detector=detector,
        frame_w_px=FRAME_W_PX,
        car_width_m=CAR_W_M,
        lane_half_width_m=LANE_HALF_M,
    )
    assert result.model_dump() == {
        "frame": 120,
        "time": 4.0,
        "lead": {"id": 3, "box": [450.0, 700.0, 550.0, 800.0]},
        "cut_in": False,
    }
