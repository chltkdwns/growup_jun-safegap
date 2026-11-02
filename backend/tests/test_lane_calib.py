"""사다리꼴 자동 설정 단위 테스트. 영상 없이 가짜 직선으로 확인한다.

실행 (backend 폴더에서): python -m pytest tests
"""

import cv2
import numpy as np
import pytest

from app.perception.lane_calib import (
    CalibrationError,
    calibrate_trapezoid,
    estimate_hood_ratio,
    estimate_vanishing_point,
    trapezoid_from_vp,
)


def segments_toward(vp: tuple[float, float], xs_bottom: list[float], y_bottom: float) -> np.ndarray:
    """소실점 vp로 향하는 테스트용 직선 조각들 (아래쪽 x에서 소실점 쪽으로 절반만)."""
    segs = []
    for x in xs_bottom:
        mid_x, mid_y = (x + vp[0]) / 2, (y_bottom + vp[1]) / 2
        segs.append([x, y_bottom, mid_x, mid_y])
    return np.array(segs, dtype=float)


def test_vanishing_point_found_from_converging_lines():
    segs = segments_toward((500, 400), [100, 200, 300, 700, 800, 900], 900)
    vp = estimate_vanishing_point(segs, 1000, 1000, min_inliers=6)
    assert vp is not None
    assert abs(vp[0] - 500) < 1 and abs(vp[1] - 400) < 1


def test_no_vanishing_point_when_too_few_lines():
    segs = segments_toward((500, 400), [200, 800], 900)
    assert estimate_vanishing_point(segs, 1000, 1000, min_inliers=10) is None


def test_trapezoid_edges_point_to_vanishing_point():
    trap = trapezoid_from_vp(
        (500, 400),
        1000,
        1000,
        hood_ratio=0.3,
        lane_half_width_ratio=0.2,
        lane_top_ratio=0.1,
    )
    # 아래 변: 본넷 경계(y 700)에서 x 300~700
    assert np.allclose(trap[2], [700, 700]) and np.allclose(trap[3], [300, 700])
    # 위 변: 소실점~본넷의 10% 지점(y 430), 폭도 10%로 줄어 x 480~520
    assert np.allclose(trap[0], [480, 430]) and np.allclose(trap[1], [520, 430])


def test_hood_ratio_from_where_lane_segments_end():
    # 차선 조각이 y 700에서 끝나면 본넷은 아래 30%
    segs = segments_toward((500, 400), [100, 200, 300, 700, 800, 900], 700)
    # 본넷 반사: 소실점을 향하지 않는 조각은 무시돼야 한다
    reflection = np.array([[300, 950, 400, 800], [700, 950, 600, 800]], dtype=float)
    hood = estimate_hood_ratio(np.vstack([segs, reflection]), (500, 400), 1000, percentile=90)
    assert abs(hood - 0.3) < 0.01


def write_black_video(path, n_frames: int = 30, size: int = 64) -> str:
    """차선이 없는 검은 화면 영상. 자동 보정이 실패하는 경우를 만든다."""
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (size, size))
    for _ in range(n_frames):
        writer.write(np.zeros((size, size, 3), dtype=np.uint8))
    writer.release()
    return str(path)


def test_manual_mode_uses_camera_values():
    cfg = {
        "auto_lane": False,
        "lane_trapezoid": [[0.4, 0.5], [0.6, 0.5], [0.8, 0.9], [0.2, 0.9]],
        "hood_ratio": 0.1,
    }
    trap, vp, hood = calibrate_trapezoid("unused.mp4", 1000, 1000, cfg)
    assert np.allclose(trap[0], [400, 500]) and np.allclose(trap[2], [800, 900])
    assert vp is None and hood == 0.1


def test_manual_mode_without_camera_values_raises():
    cfg = {"auto_lane": False}  # 기본 사다리꼴이 없으므로 카메라 값이 없으면 멈춘다
    with pytest.raises(CalibrationError):
        calibrate_trapezoid("unused.mp4", 1000, 1000, cfg)


def test_auto_mode_raises_when_no_lane_found(tmp_path):
    cfg = {"auto_lane": True, "calib_sample_frames": 5, "vp_min_inliers": 100}
    video = write_black_video(tmp_path / "black.mp4")
    with pytest.raises(CalibrationError):
        calibrate_trapezoid(video, 64, 64, cfg)
