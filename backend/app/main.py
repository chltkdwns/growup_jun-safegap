import asyncio
import itertools
import json
import re
from collections.abc import Callable, Iterator
from pathlib import Path

import cv2
import numpy as np
import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.config import load_config
from app.judgment.distance import resolve_focal_px
from app.judgment.judge import FrameJudge
from app.schemas import FrameResult, SetSpeed

# ---- mock 값 ----
# A 인식기가 연결되면 이 상수들과 mock_box_px(), mock 상황 함수, /ws의 mock 루프를 지운다.
# 판단(거리·TTC·경고 단계·이유)은 mock도 B의 FrameJudge가 한다. 여기서는 박스만 가짜로 만든다.
MOCK_START_DISTANCE_M = 60.0  # 처음 앞차 거리(m)
MOCK_STEP_M = 0.5  # 프레임마다 가까워지는 거리(m)
MOCK_MIN_DISTANCE_M = 5.0  # 이보다 가까워지면 처음 거리로 되돌린다(m)
MOCK_INTERVAL_S = 0.1  # 프레임 전송 간격(초)
MOCK_FOCAL_PX = 1150.0  # 핀홀 공식 역산용 초점거리(px)
MOCK_CAR_W_M = 1.8  # 앞차 실제 폭(m)
MOCK_CAR_H_M = 1.45  # 앞차 실제 높이(m)
MOCK_CAM_H_M = 1.35  # 카메라 높이(m): 박스 아래 변 위치 계산용
MOCK_FRAME_W_PX = 1920.0  # mock 박스 좌표의 기준 화면 가로(px)
MOCK_CENTER_X_PX = 960.0  # 화면 가로 중앙(px). 박스가 이 선 위에 선다
MOCK_HORIZON_Y_PX = 470.0  # 지평선 높이(px). 먼 차일수록 박스가 이 선에 가까워진다
MOCK_SPEED_KMH = 50.0  # 내 속도(km/h). 지금은 고정값
# 끼어들기 시나리오: 앞차가 천천히 다가오는 중에 옆 차가 끼어든다
MOCK_CUT_IN_START_DISTANCE_M = 40.0  # 시작 거리(m)
MOCK_CUT_IN_REL_MPS = 2.0  # 가까워지는 속도(m/s)
MOCK_CUT_IN_FROM_S = 2.0  # 끼어들기가 시작되는 시각(초)
MOCK_CUT_IN_TO_S = 5.0  # 끼어들기가 끝나는 시각(초)
MOCK_CUT_IN_DURATION_S = 8.0  # 시나리오 길이(초)
# 급정거 시나리오: 앞차가 잠시 일정하게 가다가 급히 서서 빠르게 가까워진다
MOCK_BRAKE_START_DISTANCE_M = 35.0  # 시작 거리(m)
MOCK_BRAKE_DELAY_S = 1.0  # 급정거가 시작되는 시각(초)
MOCK_BRAKE_ACCEL_MPS2 = 6.0  # 가까워지는 속도가 늘어나는 정도(m/s²)
MOCK_BRAKE_MAX_REL_MPS = 15.0  # 가까워지는 속도의 상한(m/s)

# 재생 모드: /ws?mode=replay&video_id=<영상 이름> 으로 연결하면 outputs/<영상 이름>.json을 재생한다
BACKEND_DIR = Path(__file__).resolve().parent.parent
VIDEO_ID_PATTERN = re.compile(r"^[\w.\-]+$")  # 경로 이동(../)을 막으려고 글자·숫자·.-_ 만 허용
WS_POLICY_VIOLATION = 1008  # 잘못된 요청으로 연결을 닫을 때 쓰는 WebSocket 종료 코드

# 실시간 모드: /ws?mode=live 로 연결해 화면이 JPEG 프레임을 보낸다 (폰 카메라 설정은 config.yaml의 api.live_phone_config)
# 프레임 메시지 = 앞 4바이트 프레임 번호 + 다음 4바이트 촬영 시각(ms, 카메라를 켠 뒤 지난 시간) + JPEG. 모두 빅엔디안 정수
FRAME_INDEX_BYTES = 4
FRAME_TIME_BYTES = 4
FRAME_HEADER_BYTES = FRAME_INDEX_BYTES + FRAME_TIME_BYTES
MS_PER_S = 1000.0  # 촬영 시각(ms) → 초 변환

# uvicorn이 `app.main:app`으로 이 객체를 찾아 실행한다
app = FastAPI(title="BreakTime API")


@app.get("/health")
def health() -> dict[str, bool]:
    """서버가 살아 있는지 알려 준다.

    사용처: C(통합) 단계. 프론트엔드와 uvicorn 기동 직후 연결 확인에서 호출한다.
    입력: 없음
    출력: {"ok": True}
    """
    # 연결 확인용이라 상태 검사 없이 항상 ok를 돌려준다
    return {"ok": True}


def mock_box_px(distance_m: float) -> tuple[float, float, float, float]:
    """거리에서 거꾸로 앞차 박스를 만든다 (핀홀 공식 역산).

    사용처: mock_perceptions()와 fake_perception_stream()이 mock 박스를 만들 때 호출한다.
    입력: distance_m 앞차까지 거리(m)
    출력: (x1, y1, x2, y2) 화면 픽셀. 화면 가운데 앞에 서 있는 차로 가정한다.
    주의: mock 전용. 실제 박스는 A(인식)의 검출 결과로 대체된다.
    """
    # 가까울수록 크게: 화면 속 1m의 크기(px) = 초점거리 ÷ 거리
    px_per_m = MOCK_FOCAL_PX / distance_m
    half_w = MOCK_CAR_W_M / 2 * px_per_m
    bottom = MOCK_HORIZON_Y_PX + MOCK_CAM_H_M * px_per_m
    top = bottom - MOCK_CAR_H_M * px_per_m
    return (MOCK_CENTER_X_PX - half_w, top, MOCK_CENTER_X_PX + half_w, bottom)


def mock_approach() -> Iterator[tuple[float, float, bool]]:
    """앞차가 일정한 속도로 계속 다가오는 mock 상황 (안전거리 부족 → TTC 경고).

    사용처: mock_perceptions()와 fake_perception_stream()이 mock_cut_in, mock_hard_brake와 번갈아 돌린다.
    출력: 프레임마다 (거리 m, 가까워지는 속도 m/s, 끼어들기 여부)
    """
    distance_m = MOCK_START_DISTANCE_M
    while distance_m >= MOCK_MIN_DISTANCE_M:
        yield distance_m, MOCK_STEP_M / MOCK_INTERVAL_S, False
        distance_m -= MOCK_STEP_M


def mock_cut_in() -> Iterator[tuple[float, float, bool]]:
    """앞차가 천천히 다가오는 중에 옆 차가 끼어드는 mock 상황.

    사용처: mock_perceptions()와 fake_perception_stream()이 mock_approach, mock_hard_brake와 번갈아 돌린다.
    출력: 프레임마다 (거리 m, 가까워지는 속도 m/s, 끼어들기 여부)
    주의: 끼어드는 동안(FROM~TO초)만 끼어들기 여부가 True다.
    """
    distance_m = MOCK_CUT_IN_START_DISTANCE_M
    for step in range(int(MOCK_CUT_IN_DURATION_S / MOCK_INTERVAL_S)):
        elapsed_s = step * MOCK_INTERVAL_S
        cut_in = MOCK_CUT_IN_FROM_S <= elapsed_s < MOCK_CUT_IN_TO_S
        yield distance_m, MOCK_CUT_IN_REL_MPS, cut_in
        distance_m -= MOCK_CUT_IN_REL_MPS * MOCK_INTERVAL_S


def mock_hard_brake() -> Iterator[tuple[float, float, bool]]:
    """앞차가 급정거해 빠르게 가까워지는 mock 상황.

    사용처: mock_perceptions()와 fake_perception_stream()이 mock_approach, mock_cut_in과 번갈아 돌린다.
    출력: 프레임마다 (거리 m, 가까워지는 속도 m/s, 끼어들기 여부)
    """
    distance_m = MOCK_BRAKE_START_DISTANCE_M
    elapsed_s = 0.0
    while distance_m >= MOCK_MIN_DISTANCE_M:
        # 급정거 시각 전에는 0, 그 뒤로 일정하게 빨라지다 상한에서 멈춘다
        rel_speed_mps = min(
            MOCK_BRAKE_MAX_REL_MPS,
            max(0.0, MOCK_BRAKE_ACCEL_MPS2 * (elapsed_s - MOCK_BRAKE_DELAY_S)),
        )
        yield distance_m, rel_speed_mps, False
        distance_m -= rel_speed_mps * MOCK_INTERVAL_S
        elapsed_s += MOCK_INTERVAL_S


def mock_perceptions() -> Iterator[dict]:
    """mock 상황 셋을 차례로 끝없이 돌며 A→B 형식(PerceptionFrame 모양)의 프레임을 만든다.

    사용처: ws_frames()의 mock 모드가 프레임마다 하나씩 꺼내 FrameJudge에 넣는다.
    출력: {"frame", "time", "lead": {"id", "box"}, "cut_in"}
    주의: 상황이 바뀔 때마다 앞차 id를 새로 붙인다 (B가 앞차가 바뀐 것으로 알고 TTC 기록을 새로 쌓는다).
    """
    frame_idx = 0
    for lead_id, factory in enumerate(itertools.cycle([mock_approach, mock_cut_in, mock_hard_brake]), start=1):
        for distance_m, _, cut_in in factory():
            yield {
                "frame": frame_idx,
                "time": frame_idx * MOCK_INTERVAL_S,
                "lead": {"id": lead_id, "box": list(mock_box_px(distance_m))},
                "cut_in": cut_in,
            }
            frame_idx += 1


def to_frame_result(perception: dict, judged: dict) -> FrameResult:
    """A의 인식 결과와 B의 판단 결과를 화면용 FrameResult 하나로 합친다.

    사용처: mock(ws_frames), 재생(replay_frame), 실시간(live_frames)이 프레임마다 호출한다.
    입력: perception {"time", "lead": {"box"} 또는 None, ...} (A 결과),
          judged FrameJudge.judge_frame()의 출력 {"distance_m", "ttc_s", "level", "rel_speed_mps", "safe_distance_m", "event", "speed_kmh"}
    출력: FrameResult. 앞차가 없으면 lead_box_px는 None
    주의: 값은 B가 계산한 그대로 쓴다 (C는 판단하지 않는다). 속도를 모르면 speed_kmh·safe_distance_m이 None이다.
    """
    lead = perception["lead"]
    return FrameResult(
        distance_m=judged["distance_m"],
        lead_box_px=tuple(lead["box"]) if lead else None,
        speed_kmh=judged["speed_kmh"],
        rel_speed_mps=judged["rel_speed_mps"],
        ttc_s=judged["ttc_s"],
        safe_distance_m=judged["safe_distance_m"],
        level=judged["level"],
        event=judged["event"],
        time_s=perception["time"],
    )


def load_replay(video_id: str) -> list[dict]:
    """분석 결과 JSON(outputs/<video_id>.json)을 읽어 프레임 dict 리스트로 돌려준다.

    사용처: ws_frames()가 재생 모드 연결 때 한 번 호출한다.
    입력: video_id 영상 이름 (확장자 제외). scripts/analyze_and_judge.py가 저장한 파일 이름과 같다
    출력: 프레임별 인식 결과와 판단 결과를 합친 dict ("frame", "time", "lead", "cut_in"과 FrameJudge 출력)
    주의: 형식이 안 맞는 이름이거나 파일이 없으면 FileNotFoundError를 낸다 (바깥에서 연결을 닫는다).
    """
    # 1단계: 이름 검사 (화면이 보낸 값이라 믿지 않는다)
    if not VIDEO_ID_PATTERN.fullmatch(video_id):
        raise FileNotFoundError(video_id)
    # 2단계: 설정의 결과 폴더에서 파일을 읽는다
    output_dir = BACKEND_DIR / load_config()["paths"]["output_dir"]
    with open(output_dir / f"{video_id}.json", encoding="utf-8") as f:
        return json.load(f)


def replay_frame(record: dict) -> FrameResult:
    """재생할 프레임 하나(A+B 합친 결과)를 화면용 FrameResult로 바꾼다.

    사용처: replay_frames()가 재생 모드에서 매 프레임 호출한다.
    입력: record load_replay()가 돌려준 프레임 하나
    출력: FrameResult. 앞차가 없으면 distance_m·lead_box_px·ttc_s는 None
    주의: record에 B의 출력(rel_speed_mps 등)이 있어야 한다. 예전 형식 JSON이면 analyze_and_judge.py로 다시 만든다.
    """
    return to_frame_result(record, record)


async def receive_commands(websocket: WebSocket, state: dict[str, float]) -> None:
    """화면이 보낸 요청을 계속 받아 상태에 반영한다 (지금은 내 속도 바꾸기만).

    사용처: ws_frames()가 연결마다 이 함수를 백그라운드로 돌린다.
    입력: websocket 연결, state 연결 하나의 공유 상태 (speed_kmh 키 사용)
    출력: 없음. 연결이 끊기면 조용히 끝난다.
    주의: 모양이 틀리거나 범위를 벗어난 요청은 무시한다 (화면 입력은 믿지 않는다).
    """
    try:
        while True:
            # 1단계: 요청 문자열 받기 (연결이 끊기면 WebSocketDisconnect)
            raw = await websocket.receive_text()
            # 2단계: 스키마로 검증. 틀린 요청은 버린다
            try:
                command = SetSpeed.model_validate_json(raw)
            except ValidationError:
                continue
            # 3단계: 다음 프레임부터 새 속도로 계산된다
            state["speed_kmh"] = command.speed_kmh
    except WebSocketDisconnect:
        pass


async def replay_frames(websocket: WebSocket, video_id: str) -> None:
    """저장된 분석 결과를 영상 시간에 맞춰 화면에 보낸다. 끝나면 처음부터 반복한다.

    사용처: ws_frames()가 mode=replay 연결에서 호출한다.
    입력: websocket 연결, video_id 영상 이름 (outputs/<video_id>.json)
    출력: FrameResult JSON을 JSON의 time(초)에 맞춰 전송. time_s에 영상 위치를 담는다
    주의: 결과 파일이 없거나 프레임이 0개이면 종료 코드 1008로 연결을 닫는다. 화면이 보내는 set_speed는 무시한다
          (속도는 분석할 때 이미 반영됐다).
    """
    # 1단계: 결과 파일 읽기. 없으면 연결 종료
    try:
        records = load_replay(video_id)
    except FileNotFoundError:
        await websocket.close(code=WS_POLICY_VIOLATION)
        return
    # 프레임이 하나도 없는 결과 파일은 재생할 것이 없으므로 같은 방식으로 닫는다
    if not records:
        await websocket.close(code=WS_POLICY_VIOLATION)
        return

    # 화면이 연결을 끊는 것을 알아채려고 요청 받는 작업을 같이 돌린다
    receiver = asyncio.create_task(receive_commands(websocket, {}))
    loop = asyncio.get_running_loop()
    # 마지막 프레임이 화면에 머무는 시간(초). 프레임 간 평균 간격으로 어림한다
    frame_interval_s = records[-1]["time"] / max(1, len(records) - 1)
    try:
        while not receiver.done():
            # 2단계: 시작 시각을 기준으로 각 프레임의 time에 맞춰 보낸다. 끝까지 보냈으면 처음부터 다시
            # (프레임마다 sleep하면 전송 시간이 쌓여 영상보다 느려지므로 시작 시각 기준으로 기다린다)
            started_s = loop.time()
            for record in records:
                if receiver.done():
                    break
                await asyncio.sleep(max(0.0, started_s + record["time"] - loop.time()))
                await websocket.send_text(replay_frame(record).model_dump_json())
            # 마지막 프레임 길이만큼 더 기다려야 영상 길이와 반복 주기가 같다
            await asyncio.sleep(max(0.0, started_s + records[-1]["time"] + frame_interval_s - loop.time()))
    except WebSocketDisconnect:
        pass
    finally:
        receiver.cancel()


def fake_perception_stream() -> Callable[[np.ndarray, int, float], dict]:
    """A(인식)가 아직 없을 때 쓰는 가짜 인식기를 만든다 (mock 상황의 거리로 앞차 박스를 만든다).

    사용처: live_frames()가 연결마다 한 번 호출한다. A의 PerceptionStream이 오면 PERCEPTION_FACTORY를 바꿔 끼운다.
    입력: 없음
    출력: (이미지, 프레임 번호, 촬영 시각 초) → PerceptionFrame 모양의 dict를 돌려주는 함수
    주의: 이미지는 보지 않는다. mock 상황을 프레임 순서대로 돌려 쓸 뿐이다.
    """
    situations = itertools.chain.from_iterable(
        factory() for factory in itertools.cycle([mock_approach, mock_cut_in, mock_hard_brake])
    )

    def perceive(image: np.ndarray, frame_idx: int, time_s: float) -> dict:
        distance_m, _, cut_in = next(situations)
        # mock 박스는 1920px 기준이라, 실제 이미지 가로에 맞춰 줄인다
        scale = image.shape[1] / MOCK_FRAME_W_PX
        box = [v * scale for v in mock_box_px(distance_m)]
        return {"frame": frame_idx, "time": time_s, "lead": {"id": 1, "box": box}, "cut_in": cut_in}

    return perceive


# 연결마다 인식기를 만드는 함수. A(인식)가 완성되면 이 자리에 실제 인식기를 넣는다
PERCEPTION_FACTORY: Callable[[], Callable[[np.ndarray, int, float], dict]] = fake_perception_stream


def load_phone_config(cfg: dict) -> dict:
    """폰 카메라 설정 파일(config.yaml의 api.live_phone_config)을 읽는다.

    사용처: live_frames()가 연결 때 한 번 호출한다.
    입력: cfg config 전체
    출력: 폰 설정 dict (camera 섹션에 hfov_deg 또는 focal_px)
    """
    with open(BACKEND_DIR / cfg["api"]["live_phone_config"], encoding="utf-8") as f:
        return yaml.safe_load(f)


def live_focal_px(camera_cfg: dict, frame_w_px: int, frame_h_px: int) -> float:
    """폰 카메라 설정과 받은 프레임 크기로 초점거리(px)를 구한다.

    사용처: live_frames()가 프레임을 처음 받을 때(또는 프레임 크기가 바뀔 때) 호출해 FrameJudge에 넘긴다.
    입력: camera_cfg 폰 설정의 camera 섹션, frame_w_px·frame_h_px 받은 프레임 크기(px)
    출력: 초점거리(px)
    주의: 폰 설정의 화각(hfov_deg)은 카메라의 "긴 변" 기준이다. 폰을 세로로 들면 가로가 짧은 변이 되므로,
          항상 긴 변의 길이로 계산한다. 그래야 가로·세로로 돌려도 같은 초점거리가 나온다
          (화면이 긴 변을 같은 길이로 줄여 보낸다는 전제).
    """
    # 긴 변을 "가로 폭"으로 넘겨 B의 resolve_focal_px를 그대로 쓴다
    return resolve_focal_px(camera_cfg, max(frame_w_px, frame_h_px))


async def live_frames(websocket: WebSocket, cfg: dict) -> None:
    """화면(폰)이 보낸 JPEG 프레임을 인식 → 판단해 결과를 돌려준다.

    사용처: ws_frames()가 mode=live 연결에서 호출한다.
    입력: websocket 연결, cfg config 전체 (폰 카메라 설정은 api.live_phone_config 파일)
    출력: 처리한 프레임마다 FrameResult JSON (frame, frame_w_px, frame_h_px 포함)
    주의: 초점거리는 화면이 아니라 서버가 정한다 (화면이 보낸 값은 믿지 않는다). 첫 프레임의 크기로 계산하고,
          프레임 크기가 바뀌면 다시 계산한다(이때 TTC 기록은 처음부터 다시 쌓인다).
          시간은 화면이 프레임에 담아 보낸 촬영 시각을 쓴다 (프레임 간격이 일정하지 않아도 TTC가 맞도록).
          처리가 프레임 도착보다 느리면 가장 최근 프레임만 처리하고 나머지는 버린다(지연이 쌓이지 않게).
          화면이 보내는 set_speed는 다음 프레임부터 적용된다.
    """
    # 1단계: 연결 하나의 상태 준비 (연결마다 새로 만든다)
    state = {"speed_kmh": cfg["api"]["live_default_speed_kmh"]}
    latest: dict = {}  # 가장 최근에 도착한 프레임 {"frame_idx", "time_s", "jpeg"}. 새 프레임이 오면 덮어쓴다
    new_frame = asyncio.Event()
    camera_cfg = load_phone_config(cfg)["camera"]
    judge: FrameJudge | None = None  # 첫 프레임 크기를 알아야 초점거리를 구할 수 있어 그때 만든다
    judge_frame_size: tuple[int, int] | None = None
    perceive = PERCEPTION_FACTORY()

    async def receive_loop() -> None:
        """화면이 보낸 프레임(바이너리)과 set_speed(문자열)를 계속 받는다."""
        try:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    return
                data = message.get("bytes")
                if data is not None:
                    # 프레임: 앞 4바이트 번호 + 4바이트 촬영 시각(ms) + JPEG. 너무 짧으면 버린다
                    if len(data) > FRAME_HEADER_BYTES:
                        latest["frame_idx"] = int.from_bytes(data[:FRAME_INDEX_BYTES], "big")
                        time_ms = int.from_bytes(data[FRAME_INDEX_BYTES:FRAME_HEADER_BYTES], "big")
                        latest["time_s"] = time_ms / MS_PER_S
                        latest["jpeg"] = data[FRAME_HEADER_BYTES:]
                        new_frame.set()
                elif message.get("text") is not None:
                    try:
                        state["speed_kmh"] = SetSpeed.model_validate_json(message["text"]).speed_kmh
                    except ValidationError:
                        continue
        finally:
            new_frame.set()  # 기다리는 처리 루프가 끝나도록 깨운다

    receiver = asyncio.create_task(receive_loop())
    try:
        while True:
            # 2단계: 새 프레임을 기다린다. 연결이 끊겼으면 끝낸다
            await new_frame.wait()
            if receiver.done():
                break
            new_frame.clear()
            frame_idx, time_s, jpeg = latest["frame_idx"], latest["time_s"], latest["jpeg"]

            # 3단계: JPEG를 이미지로 풀기. 깨진 프레임은 건너뛴다
            image = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                continue
            frame_h_px, frame_w_px = image.shape[:2]

            # 초점거리는 프레임 크기로 정한다. 처음이거나 크기가 바뀌면 판단기를 새로 만든다
            if judge is None or judge_frame_size != (frame_w_px, frame_h_px):
                focal_px = live_focal_px(camera_cfg, frame_w_px, frame_h_px)
                judge = FrameJudge(cfg["judgment"], focal_px=focal_px)
                judge_frame_size = (frame_w_px, frame_h_px)

            # 4단계: 인식은 오래 걸리므로 별도 스레드에서 돌려 서버(속도 요청 수신)가 멈추지 않게 한다
            perception = await asyncio.to_thread(perceive, image, frame_idx, time_s)

            # 5단계: 판단 후 화면용 결과로 바꿔 보낸다
            judged = judge.judge_frame(perception, state["speed_kmh"])
            result = to_frame_result(perception, judged).model_copy(
                update={"frame": frame_idx, "frame_w_px": frame_w_px, "frame_h_px": frame_h_px}
            )
            await websocket.send_text(result.model_dump_json())
    except WebSocketDisconnect:
        pass
    finally:
        receiver.cancel()


@app.websocket("/ws")
async def ws_frames(websocket: WebSocket) -> None:
    """모드에 따라 프레임 결과를 화면에 보낸다: 실시간(live), 재생(replay), 그 밖에는 가짜 주행 상황(mock).

    사용처: C(통합) 단계. 프론트의 useWebSocket이 연결해 FrameResult를 받는다.
    입력: 주소의 mode=live / mode=replay&video_id=... / 없음(mock). 화면이 보내는 set_speed(SetSpeed)로 내 속도를 바꿀 수 있다
    출력: FrameResult JSON (mock은 MOCK_INTERVAL_S마다)
    주의: mock은 실제 분석 결과가 아니다. 상황이 끝나면 다음 상황으로 넘어가고, 셋을 끝내면 처음부터 반복한다.
    """
    # 1단계: 연결 수락. mode에 따라 실시간·재생으로 넘긴다
    await websocket.accept()
    if websocket.query_params.get("mode") == "live":
        await live_frames(websocket, load_config())
        return
    if websocket.query_params.get("mode") == "replay":
        await replay_frames(websocket, websocket.query_params.get("video_id", ""))
        return

    # 2단계 (mock): 세 가지 상황(접근, 끼어들기, 급정거)의 프레임을 B의 FrameJudge에 넣어 판단한다
    judge = FrameJudge(load_config()["judgment"], focal_px=MOCK_FOCAL_PX)
    # 연결마다 내 속도를 따로 들고, 화면 요청은 별도 작업이 받아서 여기에 반영한다
    state = {"speed_kmh": MOCK_SPEED_KMH}
    receiver = asyncio.create_task(receive_commands(websocket, state))
    try:
        for perception in mock_perceptions():
            # 화면이 끊으면 receiver가 끝나므로 같이 멈춘다
            if receiver.done():
                break
            # 3단계: 판단하고, 스키마로 검증해 전송 (스키마에 없는 값은 못 나간다)
            judged = judge.judge_frame(perception, state["speed_kmh"])
            await websocket.send_text(to_frame_result(perception, judged).model_dump_json())

            # 4단계: 다음 프레임까지 대기 (서버가 멈추지 않게 await로 쉰다)
            await asyncio.sleep(MOCK_INTERVAL_S)
    except WebSocketDisconnect:
        # 화면이 연결을 끊으면 조용히 끝낸다
        pass
    finally:
        # 받는 작업이 남아 있으면 같이 정리한다
        receiver.cancel()
