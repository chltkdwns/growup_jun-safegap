from app.config import load_config
from app.main import (
    MOCK_SPEED_KMH,
    app,
    mock_approach,
    mock_cut_in,
    mock_hard_brake,
    replay_frame,
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
        ws.send_json({"type": "set_speed", "speed_kmh": 80})
        frame = read_until_speed(ws, 80.0)

    assert frame is not None
    # 80km/h = 22.22m/s, x 2초 = 44.4m (기본 속도와 다른 값을 써야 "바뀌었다"를 확인할 수 있다)
    assert abs(frame["safe_distance_m"] - 44.4) < 0.1


def test_ws_ignores_invalid_set_speed() -> None:
    """범위를 벗어난 속도는 무시하고 기존 속도를 유지하는지 확인한다."""
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "set_speed", "speed_kmh": -5})
        ws.send_json({"type": "set_speed", "speed_kmh": 9999})
        ws.send_text("not json")
        frames = [ws.receive_json() for _ in range(5)]

    assert all(f["speed_kmh"] == MOCK_SPEED_KMH for f in frames)


def test_mock_situations_cover_each_event() -> None:
    """세 mock 상황이 끝나고, 끼어들기와 급정거 순간을 각각 포함하는지 확인한다."""
    hard_brake_rel_mps = load_config()["judgment"]["hard_brake_rel_mps"]
    assert len(list(mock_approach())) > 0
    assert any(cut_in for _, _, cut_in in mock_cut_in())
    assert any(rel >= hard_brake_rel_mps for _, rel, _ in mock_hard_brake())


def make_record(**changes) -> dict:
    """재생 테스트용 프레임 하나 (앞차 있음, 거리 30m, TTC 3초, 60km/h)를 만든다."""
    record = {
        "frame": 0,
        "time": 0.0,
        "lead": {"id": 1, "box": [100.0, 200.0, 300.0, 400.0]},
        "cut_in": False,
        "speed_kmh": 60.0,
        "distance_m": 30.0,
        "ttc_s": 3.0,
        "rel_speed_mps": 10.0,
        "safe_distance_m": 33.3,
        "level": "경고",
        "event": "hard_brake",
    }
    return {**record, **changes}


def test_replay_frame_uses_judged_values_as_is() -> None:
    """저장된 B의 판단값(상대 속도·안전거리·이유)을 C가 다시 계산하지 않고 그대로 쓰는지 확인한다."""
    frame = replay_frame(make_record())

    assert frame.rel_speed_mps == 10.0
    assert frame.safe_distance_m == 33.3
    assert frame.lead_box_px == (100.0, 200.0, 300.0, 400.0)
    assert frame.event == "hard_brake"
    assert frame.time_s == 0.0  # 영상 위치가 같이 나간다


def test_replay_frame_without_lead_or_speed() -> None:
    """앞차가 없으면 거리·박스·TTC가, 속도를 모르면 속도·안전거리가 None으로 나가는지 확인한다."""
    record = make_record(
        lead=None, distance_m=None, ttc_s=None, level="정상", event=None,
        rel_speed_mps=0.0, speed_kmh=None, safe_distance_m=None,
    )
    frame = replay_frame(record)

    assert frame.distance_m is None
    assert frame.lead_box_px is None
    assert frame.ttc_s is None
    assert frame.speed_kmh is None
    assert frame.safe_distance_m is None
    assert frame.event is None


def test_ws_replay_rejects_unknown_video() -> None:
    """없는 영상 이름이나 ../ 가 섞인 이름은 연결을 닫는지 확인한다."""
    import pytest
    from starlette.websockets import WebSocketDisconnect

    for video_id in ("no_such_video", "..%2Fconfig"):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"/ws?mode=replay&video_id={video_id}") as ws:
                ws.receive_json()


def test_ws_replay_closes_on_empty_result(tmp_path, monkeypatch) -> None:
    """프레임이 0개인 결과 파일이면 오류 없이 연결을 닫는지 확인한다."""
    import pytest
    from starlette.websockets import WebSocketDisconnect

    monkeypatch.setattr("app.main.load_replay", lambda video_id: [])
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws?mode=replay&video_id=empty") as ws:
            ws.receive_json()
