import pytest

from app.judgment.distance import estimate_distance_m, focal_px_from_hfov
from test_fake_input import box_w, load

F_PX = 1000      # make_fake_input.py와 같은 가짜 초점거리
CAR_W_M = 1.8


def test_distance_matches_truth_on_fake_input():
    rows = load("approach")
    # t=0초 정답 50m, t=2초(60프레임) 정답 30m
    assert estimate_distance_m(box_w(rows[0]), F_PX, CAR_W_M) == pytest.approx(50, rel=0.01)
    assert estimate_distance_m(box_w(rows[60]), F_PX, CAR_W_M) == pytest.approx(30, rel=0.01)


def test_focal_px_from_hfov():
    # 화각 90도면 tan(45°)=1 → 초점거리 = 화면 폭의 절반
    assert focal_px_from_hfov(1920, 90) == pytest.approx(960)
