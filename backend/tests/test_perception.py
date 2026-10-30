"""A(인식) 단위 테스트. YOLO 없이 가짜 박스로 앞차 선정과 끼어들기를 확인한다.

실행 (backend 폴더에서): python -m pytest tests
"""

from app.perception.cut_in import CutInDetector
from app.perception.lane import trapezoid_to_px
from app.perception.lead import select_lead
from app.perception.pipeline import perceive_frame

# 1000x1000 화면에서 x 400~600(위), 200~800(아래), y 500~900인 사다리꼴
TRAPEZOID_PX = trapezoid_to_px([[0.4, 0.5], [0.6, 0.5], [0.8, 0.9], [0.2, 0.9]], 1000, 1000)


def box_at(center_x: float, bottom_y: float, width: float = 100) -> list[float]:
    """아래쪽 가운데 점이 (center_x, bottom_y)인 테스트용 박스."""
    return [center_x - width / 2, bottom_y - width, center_x + width / 2, bottom_y]


def test_lead_is_largest_box_inside():
    tracks = {
        1: box_at(500, 600, width=80),  # 안, 멀리
        2: box_at(500, 800, width=200),  # 안, 가까이 → 앞차
        3: box_at(100, 850, width=300),  # 바깥, 제일 큼
    }
    assert select_lead(tracks, TRAPEZOID_PX) == 2


def test_no_lead_when_all_outside():
    assert select_lead({1: box_at(100, 800)}, TRAPEZOID_PX) is None


def test_cut_in_when_crossing_boundary():
    detector = CutInDetector(approach_frames=5)
    assert detector.update({1: box_at(150, 800)}, TRAPEZOID_PX) is False  # 바깥
    assert detector.update({1: box_at(400, 800)}, TRAPEZOID_PX) is True  # 안으로 들어옴


def test_cut_in_after_n_approach_frames():
    detector = CutInDetector(approach_frames=3)
    xs = [100, 110, 120, 130]  # 바깥에서 조금씩 다가옴
    flags = [detector.update({1: box_at(x, 800)}, TRAPEZOID_PX) for x in xs]
    # 첫 프레임은 기준, 그 뒤 3프레임 연속 접근한 마지막 프레임에서 감지
    assert flags == [False, False, False, True]


def test_no_cut_in_for_car_already_inside_or_moving_away():
    detector = CutInDetector(approach_frames=2)
    for x in [150, 140, 130]:  # 바깥에서 멀어짐
        assert detector.update({1: box_at(x, 800), 2: box_at(500, 800)}, TRAPEZOID_PX) is False


def test_perceive_frame_matches_interface():
    detector = CutInDetector(approach_frames=5)
    result = perceive_frame({3: box_at(500, 800)}, frame_idx=120, fps=30.0,
                            trapezoid_px=TRAPEZOID_PX, cut_in_detector=detector)
    assert result.model_dump() == {
        "frame": 120,
        "time": 4.0,
        "lead": {"id": 3, "box": [450.0, 700.0, 550.0, 800.0]},
        "cut_in": False,
    }
