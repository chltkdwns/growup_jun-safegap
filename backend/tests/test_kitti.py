from pathlib import Path

import pytest

from app.data_sources.kitti import labels_to_ab, read_focal_px, read_speeds_kmh

MINI = Path(__file__).resolve().parent / "fixtures" / "kitti_mini"   # 직접 만든 가짜 KITTI 형식 파일


def test_read_focal_px_uses_p2():
    assert read_focal_px(MINI / "calib" / "0000.txt") == 700.0


def test_read_speeds_converts_ms_to_kmh():
    speeds = read_speeds_kmh(MINI / "oxts" / "0000.txt")
    assert len(speeds) == 10
    assert speeds[0] == pytest.approx(72.0)   # 20 m/s × 3.6


def test_labels_pick_closest_car_in_my_lane():
    rows, truth = labels_to_ab(MINI / "label_02" / "0000.txt", n_frames=10, lane_half_width_m=1.8, fps=10)
    assert len(rows) == 10
    assert rows[0]["lead"]["id"] == 3       # 옆 차선 차(id 5)가 더 가까워도 제외
    assert truth[0] == pytest.approx(30.0)
    assert rows[0]["cut_in"] is False


def test_frames_without_label_have_no_lead():
    rows, truth = labels_to_ab(MINI / "label_02" / "0000.txt", n_frames=12, lane_half_width_m=1.8, fps=10)
    assert rows[11]["lead"] is None and truth[11] is None
