"""
요약: C(통합)가 화면과 주고받는 /ws 응답(FrameResult)과 요청(SetSpeed)의 형식.
사용처: backend/app/main.py의 /ws, 프론트 useWebSocket.ts
주의: A→B→C 사이 형식은 schemas.py(팀 공용)에 있다. 이 파일은 C(화면) 전용이라 따로 두었다.
      필드를 바꾸면 프론트 useWebSocket.ts의 FrameResult와 mock(main.py), 테스트를 같이 고친다.
"""

from typing import Literal

from pydantic import BaseModel, Field

# 화면용 경고 단계. 프론트 constants.ts의 Level과 같은 영어 이름이어야 한다.
# schemas.py의 Level("정상"~"위험", B가 사용)과 이름이 달라 UiLevel로 나눴다
UiLevel = Literal["safe", "caution", "warning", "danger"]
# 낮은 단계부터 높은 단계 순서. 끼어들기로 한 단계 올릴 때 쓴다
LEVEL_ORDER: tuple[UiLevel, ...] = ("safe", "caution", "warning", "danger")

# 지금 경고가 나온 이유. 화면 배너 문구를 고른다 (경고가 없으면 None)
EventType = Literal["gap_short", "cut_in", "hard_brake"]

MAX_SPEED_KMH = (
    300.0  # 화면에서 받을 수 있는 내 속도의 상한(km/h). 이보다 크면 잘못된 값으로 본다
)


class SetSpeed(BaseModel):
    """화면이 서버로 보내는 "내 속도 바꾸기" 요청.

    사용처: C(통합) 단계. 프론트 SpeedInput이 슬라이더를 움직일 때 보내고, main.py의 receive_commands()가 받는다.
    주의: 범위를 벗어난 값은 검증에서 걸러져 무시된다. GPS 속도가 연결되면 이 요청은 대체될 수 있다.
    """

    type: Literal["set_speed"]
    speed_kmh: float = Field(ge=0, le=MAX_SPEED_KMH)  # 새 내 속도(km/h)


class FrameResult(BaseModel):
    """프레임 하나의 분석 결과. 서버가 WebSocket으로 화면에 보낸다.

    사용처: C(통합) 단계. main.py의 /ws가 매 프레임 만들어 보내고, 프론트가 받아 그린다.
    필드는 단계마다 하나씩 추가한다.
    주의: 필드를 바꾸면 프론트 useWebSocket.ts의 FrameResult와 mock(main.py), 테스트를 같이 고친다.

    """

    distance_m: float  # 앞차까지 거리(m)
    # 앞차 박스 (x1, y1, x2, y2), 화면 픽셀. 앞차가 없으면 None
    lead_box_px: tuple[float, float, float, float] | None
    speed_kmh: float  # 내 속도(km/h)
    rel_speed_mps: float  # 앞차와 가까워지는 속도(m/s). 멀어지면 음수
    # 충돌까지 남은 시간(초). 가까워지지 않으면 None
    ttc_s: float | None
    safe_distance_m: float  # 안전거리(m) = 내 속도 x 안전거리 초
    # 경고 단계. 판정은 서버(B)가 하고 화면은 색과 글자만 바꾼다
    level: UiLevel
    # 경고가 나온 이유. 단계가 safe이면 None
    event: EventType | None
