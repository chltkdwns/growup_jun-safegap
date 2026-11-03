import math

import cv2
import numpy as np
import pytest
from app.config import load_config
from app.main import app, fake_perception_stream, live_focal_px
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

client = TestClient(app)

LIVE_URL = "/ws?mode=live"


@pytest.fixture(autouse=True)
def use_fake_perception(monkeypatch) -> None:
    """테스트는 YOLO 모델을 불러오지 않도록 가짜 인식기로 바꿔 끼운다 (진짜 인식기는 아래 별도 테스트)."""
    monkeypatch.setattr("app.main.PERCEPTION_FACTORY", fake_perception_stream)


FRAME_W_PX, FRAME_H_PX = 320, 180  # 테스트용 작은 이미지


def make_frame_message(
    frame_idx: int, w_px: int = FRAME_W_PX, h_px: int = FRAME_H_PX, time_ms: int = 0
) -> bytes:
    """폰이 보내는 프레임 메시지(4바이트 번호 + 4바이트 촬영 시각 ms + JPEG)를 만든다."""
    image = np.zeros((h_px, w_px, 3), np.uint8)
    ok, jpeg = cv2.imencode(".jpg", image)
    assert ok
    return frame_idx.to_bytes(4, "big") + time_ms.to_bytes(4, "big") + jpeg.tobytes()


def test_live_focal_px_pinhole() -> None:
    """긴 변의 화각과 길이로 핀홀 초점거리를 구하는지 확인한다: (640/2) / tan(35도)."""
    assert math.isclose(
        live_focal_px({"hfov_deg": 70.0}, 640, 360), 320 / math.tan(math.radians(35))
    )


def test_live_focal_px_same_when_rotated() -> None:
    """폰을 가로로 들든 세로로 들든 같은 카메라면 초점거리가 같은지 확인한다."""
    camera_cfg = {"hfov_deg": 70.0}
    assert live_focal_px(camera_cfg, 640, 360) == live_focal_px(camera_cfg, 360, 640)


def test_ws_live_closes_without_phone_config(monkeypatch) -> None:
    """폰 설정 파일을 못 읽으면 거리를 계산할 수 없어 연결이 닫히는지 확인한다."""
    cfg = load_config()
    cfg["api"]["live_phone_config"] = "configs/no_such_phone.yaml"
    monkeypatch.setattr("app.main.load_config", lambda: cfg)
    with pytest.raises(Exception):
        with client.websocket_connect(LIVE_URL) as ws:
            ws.receive_json()


def test_ws_live_uses_capture_time() -> None:
    """결과의 time_s가 폰이 보낸 촬영 시각(ms)인지 확인한다."""
    with client.websocket_connect(LIVE_URL) as ws:
        ws.send_bytes(make_frame_message(0, time_ms=1500))
        result = ws.receive_json()

    assert result["time_s"] == 1.5


def test_ws_live_returns_result_for_frame() -> None:
    """프레임을 보내면 같은 번호와 이미지 크기가 담긴 결과가 오는지 확인한다."""
    with client.websocket_connect(LIVE_URL) as ws:
        ws.send_bytes(make_frame_message(7))
        result = ws.receive_json()

    assert result["frame"] == 7
    assert result["frame_w_px"] == FRAME_W_PX
    assert result["frame_h_px"] == FRAME_H_PX
    assert result["lead_box_px"] is not None  # 가짜 인식기가 앞차를 만든다
    assert result["level"] in ("정상", "주의", "경고", "위험")


def test_ws_live_ignores_client_focal_px() -> None:
    """주소에 focal_px를 붙여도 무시하고 서버 설정으로 계산하는지 확인한다 (화면이 보낸 값은 믿지 않는다)."""
    with client.websocket_connect(LIVE_URL + "&focal_px=1") as ws:
        ws.send_bytes(make_frame_message(0))
        result = ws.receive_json()

    assert result["distance_m"] is not None
    assert result["distance_m"] > 1  # focal_px=1을 믿었다면 거리가 1m도 안 된다


def test_ws_live_applies_set_speed_from_next_frame() -> None:
    """set_speed를 보내면 다음 프레임부터 속도와 안전거리가 바뀌는지 확인한다."""
    with client.websocket_connect(LIVE_URL) as ws:
        ws.send_bytes(make_frame_message(0))
        first = ws.receive_json()
        ws.send_json({"type": "set_speed", "speed_kmh": 100})
        ws.send_bytes(make_frame_message(1))
        second = ws.receive_json()

    assert first["speed_kmh"] == 50.0  # config 기본 속도
    assert second["speed_kmh"] == 100.0
    assert abs(second["safe_distance_m"] - 55.6) < 0.1  # 100km/h x 2초


def test_ws_live_skips_broken_jpeg() -> None:
    """깨진 JPEG는 건너뛰고 다음 정상 프레임은 처리하는지 확인한다."""
    with client.websocket_connect(LIVE_URL) as ws:
        ws.send_bytes((0).to_bytes(8, "big") + b"not a jpeg")
        ws.send_bytes(make_frame_message(1))
        result = ws.receive_json()

    assert result["frame"] == 1


def test_ws_live_handles_frame_size_change() -> None:
    """프레임 크기가 바뀌어도(폰 회전) 계속 결과를 돌려주는지 확인한다."""
    with client.websocket_connect(LIVE_URL) as ws:
        ws.send_bytes(make_frame_message(0, 320, 180))
        first = ws.receive_json()
        ws.send_bytes(make_frame_message(1, 180, 320))
        second = ws.receive_json()

    assert (first["frame_w_px"], first["frame_h_px"]) == (320, 180)
    assert (second["frame_w_px"], second["frame_h_px"]) == (180, 320)


def test_real_perception_stream_returns_perception_dict() -> None:
    """진짜 인식기가 빈 이미지에서 오류 없이 PerceptionFrame 모양을 돌려주는지 확인한다 (앞차 없음)."""
    from app.main import real_perception_stream

    perceive = real_perception_stream(load_config())
    result = perceive(np.zeros((640, 360, 3), np.uint8), 3, 0.5)

    assert result["frame"] == 3
    assert result["time"] == 0.5
    assert result["lead"] is None
