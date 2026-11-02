import asyncio
import itertools
from collections.abc import Iterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.schemas import LEVEL_ORDER, EventType, FrameResult, Level, SetSpeed

# ---- mock 값 ----
# A·B 함수가 연결되면 이 상수들과 mock_box_px(), /ws의 mock 루프를 지운다.
# 실제 서비스 값은 config.yaml로 옮길 대상이라 여기 값은 화면 테스트용 임시값이다.
MOCK_START_DISTANCE_M = 60.0  # 처음 앞차 거리(m)
MOCK_STEP_M = 0.5  # 프레임마다 가까워지는 거리(m)
MOCK_MIN_DISTANCE_M = 5.0  # 이보다 가까워지면 처음 거리로 되돌린다(m)
MOCK_INTERVAL_S = 0.1  # 프레임 전송 간격(초)
MOCK_FOCAL_PX = 1150.0  # 핀홀 공식 역산용 초점거리(px)
MOCK_CAR_W_M = 1.8  # 앞차 실제 폭(m)
MOCK_CAR_H_M = 1.45  # 앞차 실제 높이(m)
MOCK_CAM_H_M = 1.35  # 카메라 높이(m): 박스 아래 변 위치 계산용
MOCK_CENTER_X_PX = 960.0  # 화면 가로 중앙(px). 박스가 이 선 위에 선다
MOCK_HORIZON_Y_PX = 470.0  # 지평선 높이(px). 먼 차일수록 박스가 이 선에 가까워진다
MOCK_SPEED_KMH = 100.0  # 내 속도(km/h). 지금은 고정값
MOCK_SAFE_GAP_S = 2.0  # 안전거리 계산에 쓰는 초 (config의 안전거리 초)
MOCK_TTC_WARNING_S = 3.0  # TTC가 이 값 이하면 경고(초)
MOCK_TTC_DANGER_S = 1.5  # TTC가 이 값 이하면 위험(초)
MOCK_HARD_BRAKE_REL_MPS = 10.0  # 가까워지는 속도가 이 값 이상이면 급정거로 본다(m/s)
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

# 바뀌지 않는 단위 변환
KMH_TO_MS = 1 / 3.6

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

    사용처: ws_frames()가 매 프레임 mock 박스를 만들 때 호출한다.
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

    사용처: ws_frames()가 mock_cut_in, mock_hard_brake와 번갈아 돌린다.
    출력: 프레임마다 (거리 m, 가까워지는 속도 m/s, 끼어들기 여부)
    """
    distance_m = MOCK_START_DISTANCE_M
    while distance_m >= MOCK_MIN_DISTANCE_M:
        yield distance_m, MOCK_STEP_M / MOCK_INTERVAL_S, False
        distance_m -= MOCK_STEP_M


def mock_cut_in() -> Iterator[tuple[float, float, bool]]:
    """앞차가 천천히 다가오는 중에 옆 차가 끼어드는 mock 상황.

    사용처: ws_frames()가 mock_approach, mock_hard_brake와 번갈아 돌린다.
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

    사용처: ws_frames()가 mock_approach, mock_cut_in과 번갈아 돌린다.
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


def mock_level(
    distance_m: float, ttc_s: float | None, safe_distance_m: float, cut_in: bool
) -> Level:
    """TTC와 안전거리로 경고 단계를 정한다 (mock 서버용 임시 판정).

    사용처: ws_frames()가 매 프레임 level을 만들 때 호출한다.
    입력: distance_m 앞차 거리(m), ttc_s 충돌까지 남은 시간(초, 없으면 None), safe_distance_m 안전거리(m),
          cut_in 끼어들기 여부 (True이면 한 단계 올린다)
    출력: 경고 단계 (정상 / 주의 / 경고 / 위험)
    주의: mock 전용. 실제 판정은 B(judgment)가 한다.
    """
    # 1단계: 위험한 조건부터 확인한다. TTC 1.5초 이하 = 위험, 3초 이하 = 경고
    level: Level = "정상"
    if ttc_s is not None and ttc_s <= MOCK_TTC_DANGER_S:
        level = "위험"
    elif ttc_s is not None and ttc_s <= MOCK_TTC_WARNING_S:
        level = "경고"
    # TTC는 괜찮아도 안전거리보다 가까우면 주의
    elif distance_m < safe_distance_m:
        level = "주의"

    # 2단계: 끼어들기가 있으면 한 단계 올린다 (이미 위험이면 그대로)
    if cut_in and level != "위험":
        level = LEVEL_ORDER[LEVEL_ORDER.index(level) + 1]
    return level


def mock_event(level: Level, cut_in: bool, rel_speed_mps: float) -> EventType | None:
    """경고가 나온 이유를 고른다 (화면 배너 문구용).

    사용처: ws_frames()가 매 프레임 event를 만들 때 호출한다.
    입력: level 경고 단계, cut_in 끼어들기 여부, rel_speed_mps 가까워지는 속도(m/s)
    출력: "cut_in" / "hard_brake" / "gap_short" 중 하나. 안전이면 None
    주의: mock 전용. 급정거는 브레이크등이 아니라 가까워지는 속도가 급히 커진 것으로 본다.
    """
    # 안전하면 알릴 이유가 없다
    if level == "정상":
        return None
    # 이유가 겹치면 끼어들기, 급정거, 안전거리 부족 순서로 먼저 알린다
    if cut_in:
        return "cut_in"
    if rel_speed_mps >= MOCK_HARD_BRAKE_REL_MPS:
        return "hard_brake"
    return "gap_short"


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


@app.websocket("/ws")
async def ws_frames(websocket: WebSocket) -> None:
    """가짜 주행 상황(접근, 끼어들기, 급정거)을 프레임처럼 계속 보낸다.

    사용처: C(통합) 단계. 프론트의 useWebSocket이 연결해 distance_m을 받는다.
    입력: 연결만 맺으면 시작. 화면이 보내는 set_speed(SetSpeed)로 내 속도를 바꿀 수 있다
    출력: FrameResult JSON을 MOCK_INTERVAL_S마다 전송
    주의: 실제 분석 결과가 아닌 mock이다. 상황이 끝나면 다음 상황으로 넘어가고, 셋을 끝내면 처음부터 반복한다.
    """
    # 1단계: 연결 수락. 세 가지 상황(접근, 끼어들기, 급정거)을 차례로 계속 돌린다
    await websocket.accept()
    situations = itertools.chain.from_iterable(
        factory()
        for factory in itertools.cycle([mock_approach, mock_cut_in, mock_hard_brake])
    )
    # 연결마다 내 속도를 따로 들고, 화면 요청은 별도 작업이 받아서 여기에 반영한다
    state = {"speed_kmh": MOCK_SPEED_KMH}
    receiver = asyncio.create_task(receive_commands(websocket, state))
    try:
        for distance_m, rel_speed_mps, cut_in in situations:
            # 화면이 끊으면 receiver가 끝나므로 같이 멈춘다
            if receiver.done():
                break
            # 2단계: 판정에 쓸 값 계산. TTC = 거리 ÷ 가까워지는 속도, 안전거리 = 내 속도 x 2초
            ttc_s = distance_m / rel_speed_mps if rel_speed_mps > 0 else None
            speed_kmh = state["speed_kmh"]
            safe_distance_m = speed_kmh * KMH_TO_MS * MOCK_SAFE_GAP_S

            # 3단계: 단계와 이유를 정하고, 스키마로 검증해 전송 (스키마에 없는 값은 못 나간다)
            level = mock_level(distance_m, ttc_s, safe_distance_m, cut_in)
            frame = FrameResult(
                distance_m=distance_m,
                lead_box_px=mock_box_px(distance_m),
                speed_kmh=speed_kmh,
                rel_speed_mps=rel_speed_mps,
                ttc_s=ttc_s,
                safe_distance_m=safe_distance_m,
                level=level,
                event=mock_event(level, cut_in, rel_speed_mps),
            )
            await websocket.send_text(frame.model_dump_json())

            # 4단계: 다음 프레임까지 대기 (서버가 멈추지 않게 await로 쉰다)
            await asyncio.sleep(MOCK_INTERVAL_S)
    except WebSocketDisconnect:
        # 화면이 연결을 끊으면 조용히 끝낸다
        pass
    finally:
        # 받는 작업이 남아 있으면 같이 정리한다
        receiver.cancel()
