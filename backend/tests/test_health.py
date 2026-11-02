from app.main import (
    MOCK_HARD_BRAKE_REL_MPS,
    app,
    mock_approach,
    mock_cut_in,
    mock_event,
    mock_hard_brake,
    mock_level,
)
from fastapi.testclient import TestClient

# 서버를 실제로 띄우지 않고 앱을 직접 호출하는 테스트용 클라이언트
client = TestClient(app)


def test_health_returns_ok() -> None:
    """/health가 200과 {"ok": true}를 돌려주는지 확인한다."""
    # 호출
    res = client.get("/health")

    # 검증: 상태 코드와 본문
    assert res.status_code == 200
    assert res.json() == {"ok": True}


def test_mock_level_boundaries() -> None:
    """TTC 3초·1.5초, 안전거리 경계값에서 단계가 정확히 바뀌는지 확인한다."""
    safe = 50.0
    assert mock_level(60.0, 10.0, safe, False) == "정상"
    assert (
        mock_level(50.0, 10.0, safe, False) == "정상"
    )  # 안전거리와 정확히 같으면 부족하지 않다
    assert mock_level(49.9, 10.0, safe, False) == "주의"
    assert mock_level(60.0, 3.01, safe, False) == "정상"
    assert mock_level(60.0, 3.0, safe, False) == "경고"  # TTC 정확히 3초 = 경고
    assert mock_level(60.0, 1.51, safe, False) == "경고"
    assert mock_level(60.0, 1.5, safe, False) == "위험"  # TTC 정확히 1.5초 = 위험
    assert mock_level(60.0, None, safe, False) == "정상"  # 가까워지지 않으면 TTC 없음


def box_width(frame: dict) -> float:
    """프레임의 앞차 박스 폭(px)을 구한다."""
    x1, _, x2, _ = frame["lead_box_px"]
    return x2 - x1


def test_ws_sends_distance_m() -> None:
    """/ws가 distance_m이 줄어드는 프레임을 보내는지 확인한다."""
    # 연결해서 프레임 2개를 연속으로 받는다
    with client.websocket_connect("/ws") as ws:
        first = ws.receive_json()
        second = ws.receive_json()

    # 검증: 첫 프레임은 시작 거리, 다음 프레임은 더 가까워야 한다
    assert first["distance_m"] == 60.0
    assert second["distance_m"] < first["distance_m"]
    # 가까워질수록 박스 폭이 커져야 한다
    assert box_width(second) > box_width(first)


def read_until_speed(ws, speed_kmh: float, max_frames: int = 20) -> dict | None:
    """원하는 속도가 담긴 프레임이 올 때까지 최대 max_frames개 읽는다. 없으면 None."""
    for _ in range(max_frames):
        frame = ws.receive_json()
        if frame["speed_kmh"] == speed_kmh:
            return frame
    return None


def test_ws_set_speed_changes_safe_distance() -> None:
    """set_speed를 보내면 속도와 안전거리(속도 x 2초)가 따라 바뀌는지 확인한다."""
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "set_speed", "speed_kmh": 50})
        frame = read_until_speed(ws, 50.0)

    assert frame is not None
    # 50km/h = 13.89m/s, x 2초 = 27.8m
    assert abs(frame["safe_distance_m"] - 27.8) < 0.1


def test_ws_ignores_invalid_set_speed() -> None:
    """범위를 벗어난 속도는 무시하고 기존 속도를 유지하는지 확인한다."""
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "set_speed", "speed_kmh": -5})
        ws.send_json({"type": "set_speed", "speed_kmh": 9999})
        ws.send_text("not json")
        frames = [ws.receive_json() for _ in range(5)]

    assert all(f["speed_kmh"] == 100.0 for f in frames)


def test_mock_level_cut_in_raises_one_level() -> None:
    """끼어들기가 있으면 단계가 한 단계 오르고, 위험은 그대로인지 확인한다."""
    safe = 50.0
    assert mock_level(60.0, 10.0, safe, True) == "주의"  # safe -> caution
    assert mock_level(49.9, 10.0, safe, True) == "경고"  # caution -> warning
    assert mock_level(60.0, 3.0, safe, True) == "위험"  # warning -> danger
    assert mock_level(60.0, 1.5, safe, True) == "위험"  # 위험은 그대로


def test_mock_event_priority() -> None:
    """경고 이유가 겹칠 때 끼어들기, 급정거, 안전거리 부족 순으로 고르는지 확인한다."""
    assert mock_event("정상", True, 20.0) is None
    assert mock_event("경고", True, 20.0) == "cut_in"
    assert mock_event("위험", False, MOCK_HARD_BRAKE_REL_MPS) == "hard_brake"
    assert mock_event("위험", False, MOCK_HARD_BRAKE_REL_MPS - 0.1) == "gap_short"


def test_mock_situations_cover_each_event() -> None:
    """세 mock 상황이 끝나고, 끼어들기와 급정거 순간을 각각 포함하는지 확인한다."""
    assert len(list(mock_approach())) > 0
    assert any(cut_in for _, _, cut_in in mock_cut_in())
    assert any(rel >= MOCK_HARD_BRAKE_REL_MPS for _, rel, _ in mock_hard_brake())
