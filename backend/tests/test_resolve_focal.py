import pytest

from app.judgment.distance import resolve_focal_px

PHONE = {"hfov_deg": 69, "focal_px": None}   # 갤럭시 S25/S26 기본 카메라 (추정 화각)


def test_phone_1920_is_about_1400px():
    assert resolve_focal_px(PHONE, 1920) == pytest.approx(1398, abs=2)


def test_smaller_frame_scales_focal():
    # 1280px로 받으면 초점거리도 2/3로 줄어야 거리가 그대로 맞음
    assert resolve_focal_px(PHONE, 1280) == pytest.approx(resolve_focal_px(PHONE, 1920) * 2 / 3)


def test_focal_px_overrides_hfov():
    assert resolve_focal_px({"hfov_deg": 69, "focal_px": 1450}, 1920) == 1450


def test_missing_camera_values_raise():
    with pytest.raises(ValueError):
        resolve_focal_px({"hfov_deg": None, "focal_px": None}, 1920)