"""A(인식) 단위 테스트. YOLO 없이 가짜 박스로 앞차 선정과 끼어들기를 확인한다.

실행 (backend 폴더에서): python -m pytest tests
"""

from app.perception.cut_in import CutInDetector
from app.perception.lateral import lateral_offset_m
from app.perception.lead import LeadSelector
from app.perception.pipeline import perceive_frame

FRAME_W_PX = 1000
CENTER_X_PX = 500  # 정면은 화면 중앙
CAR_W_M = 1.8
LANE_HALF_M = 1.7  # 끼어들기 경계용 차선 반폭
LEAD_HALF_M = 1.2  # 앞차 후보로 보는 정면 기준 반폭 (차 중심이 이 안이어야 한다)
SWITCH_RATIO = 1.3  # 새 후보가 현재 앞차보다 넓이가 이 배 이상 커야 앞차를 바꾼다
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


def make_selector() -> LeadSelector:
    """정면 1.2m 안에서 가장 큰 차를 고르고, 1.3배 이상 커져야 앞차를 바꾸는 테스트용 선택기."""
    return LeadSelector(CAR_W_M, LEAD_HALF_M, SWITCH_RATIO)


def test_lead_is_largest_box_inside():
    tracks = {
        1: box_at(500, 80),  # 안, 멀리
        2: box_at(520, 200),  # 안, 가까이 → 앞차
        3: box_at(100, 300),  # 바깥(-2.4m), 제일 큼
    }
    assert make_selector().select(tracks, CENTER_X_PX) == 2


def test_no_lead_when_all_outside():
    assert make_selector().select({1: box_at(100)}, CENTER_X_PX) is None


def test_lead_boundary_is_inclusive():
    # 폭 100px에서 1.2m는 66.67px. 66px(1.188m)는 안, 67px(1.206m)는 밖
    assert make_selector().select({1: box_at(566)}, CENTER_X_PX) == 1
    assert make_selector().select({1: box_at(567)}, CENTER_X_PX) is None


def test_adjacent_lane_car_on_lane_line_is_not_lead():
    # 정면 트럭(0m, 넓이 22500)과 옆 차선 차(+1.7m, 넓이 25600, 더 큼): 옆 차선 차는 후보가 아니다
    tracks = {1: box_at(500, 150), 2: box_at(500 + 1.7 * 160 / 1.8, 160)}
    assert make_selector().select(tracks, CENTER_X_PX) == 1


def test_lead_is_kept_when_other_is_only_slightly_bigger():
    selector = make_selector()
    assert selector.select({1: box_at(500, 100), 2: box_at(520, 80)}, CENTER_X_PX) == 1
    # 2번이 1.2배(넓이)로 커져도 1.3배 미만이라 앞차는 1번 그대로
    assert selector.select({1: box_at(500, 100), 2: box_at(520, 109)}, CENTER_X_PX) == 1


def test_lead_switches_when_other_is_much_bigger():
    selector = make_selector()
    assert selector.select({1: box_at(500, 100), 2: box_at(520, 80)}, CENTER_X_PX) == 1
    # 2번 넓이가 1번의 1.44배(폭 120 vs 100)면 앞차를 바꾼다
    assert selector.select({1: box_at(500, 100), 2: box_at(520, 120)}, CENTER_X_PX) == 2


def test_lead_switches_when_current_lead_disappears():
    selector = make_selector()
    assert selector.select({1: box_at(500, 200), 2: box_at(520, 80)}, CENTER_X_PX) == 1
    # 1번이 사라지면 비율과 상관없이 남은 후보 중 가장 큰 차로 바뀐다
    assert selector.select({2: box_at(520, 80)}, CENTER_X_PX) == 2


def test_lead_keeps_none_state_after_no_candidates():
    selector = make_selector()
    assert selector.select({1: box_at(500, 100)}, CENTER_X_PX) == 1
    assert selector.select({}, CENTER_X_PX) is None
    # 한 번 사라졌다 돌아온 차는 새로 고르는 것과 같다
    assert selector.select({1: box_at(500, 100), 2: box_at(520, 150)}, CENTER_X_PX) == 2


def test_cut_in_when_crossing_boundary():
    # 3.6m(바깥) → 1.62m(안): 같은 쪽에서 경계를 넘어 들어옴
    assert run(make_detector(5), [box_at(700), box_at(590)]) == [False, True]


def test_no_cut_in_for_car_flickering_on_boundary():
    # 경계(1.7m) 바로 위에서 1.76m ↔ 1.64m로 흔들리는 차는 실제로 안 움직였으니 끼어들기가 아니다
    flicker = [box_at(x) for x in (598, 591, 598, 591, 598, 591)]
    assert run(make_detector(5), flicker) == [False] * 6


def test_cut_in_when_slowly_crossing_boundary_for_real():
    # 2.1 → 2.0 → 1.9 → 1.8 → 1.69m: 4프레임 동안 0.4m 이상 안쪽으로 이동해 경계를 넘었다
    xs = (616.7, 611.1, 605.6, 600, 594)
    assert run(make_detector(5), [box_at(x) for x in xs]) == [False, False, False, False, True]


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
    result = perceive_frame(
        {3: box_at(500)},
        frame_idx=120,
        fps=30.0,
        center_x_px=CENTER_X_PX,
        lead_selector=make_selector(),
        cut_in_detector=make_detector(5),
        frame_w_px=FRAME_W_PX,
    )
    assert result.model_dump() == {
        "frame": 120,
        "time": 4.0,
        "lead": {"id": 3, "box": [450.0, 700.0, 550.0, 800.0]},
        "cut_in": False,
    }
