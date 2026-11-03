"""
요약: A→B, B→C 사이에 주고받는 "한 프레임" 데이터의 형식을 정한다.
사용처: A(perception) 출력 확인, B(judgment) 입력·출력 확인, C(FastAPI) 응답 형식
입력·출력: dict(JSON 한 줄) → model_validate()로 검사 → 형식이 틀리면 ValidationError
주의: 필드 이름이나 단위를 바꾸면 A·B·C 모두에게 알리고 같이 고친다.

흐름:  영상 → [A 인식] → PerceptionFrame → [B 판단] → JudgmentFrame → [C API] → React
"""
from typing import Literal

from pydantic import BaseModel, Field

# 경고 단계는 이 4개 문자열만 허용한다. 오타("위엄")나 영어("danger")는 에러.
Level = Literal["정상", "주의", "경고", "위험"]


class LeadCar(BaseModel):
    """앞차 한 대. A가 내 차선에서 가장 가까운 차를 골라 넘긴다."""

    id: int  # 트래커(ByteTrack)가 붙인 차량 ID. 바뀌면 B가 TTC를 처음부터 다시 계산한다
    box: list[float] = Field(min_length=4, max_length=4)  # [x1, y1, x2, y2] 픽셀. 정확히 4개


class PerceptionFrame(BaseModel):
    """A → B: 한 프레임의 인식 결과.
    예: {"frame": 12, "time": 0.4, "lead": {"id": 3, "box": [520, 300, 640, 380]}, "cut_in": false}
    """

    frame: int = Field(ge=0)  # 프레임 번호 (0부터, 음수 불가)
    time: float = Field(ge=0)  # 영상 시작부터 지난 시간(초)
    lead: LeadCar | None  # 앞차가 없으면 None (JSON에서는 null)
    cut_in: bool = False  # 옆 차선 차가 끼어드는 중이면 True. 안 보내면 False


class JudgmentFrame(BaseModel):
    """B → C: 한 프레임의 판단 결과. C는 이걸 그대로 API 응답과 화면에 쓴다.
    예: {"frame": 12, "speed_kmh": 80.0, "distance_m": 25.3, "ttc_s": 2.1, "level": "경고"}
    """

    frame: int = Field(ge=0)  # PerceptionFrame의 frame과 같은 번호
    speed_kmh: float = Field(ge=0)  # 내 차 속도(km/h)
    distance_m: float | None  # 앞차까지 거리(m). 앞차가 없으면 None
    ttc_s: float | None  # 충돌까지 남은 시간(초). 프레임이 부족하거나 멀어지는 중이면 None
    level: Level  # "정상" / "주의" / "경고" / "위험" 중 하나


# ---- C(통합): 화면과 주고받는 /ws 응답·요청 ----
# 낮은 단계부터 높은 단계 순서. 끼어들기로 한 단계 올릴 때 쓴다
LEVEL_ORDER: tuple[Level, ...] = ("정상", "주의", "경고", "위험")

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

    distance_m: float | None  # 앞차까지 거리(m). 앞차가 없으면 None
    # 앞차 박스 (x1, y1, x2, y2), 화면 픽셀. 앞차가 없으면 None
    lead_box_px: tuple[float, float, float, float] | None
    speed_kmh: float | None  # 내 속도(km/h). 속도를 모르면 None
    rel_speed_mps: float  # 앞차와 가까워지는 속도(m/s). 멀어지면 음수
    # 충돌까지 남은 시간(초). 가까워지지 않으면 None
    ttc_s: float | None
    safe_distance_m: float | None  # 안전거리(m) = 내 속도 x 안전거리 초. 속도를 모르면 None
    # 경고 단계. 판정은 서버(B)가 하고 화면은 색과 글자만 바꾼다
    level: Level
    # 경고가 나온 이유. 단계가 정상이면 None
    event: EventType | None
    # 이 프레임이 영상의 몇 초 지점인지(초). 화면이 영상 위치를 맞추는 데 쓴다. 재생 모드에서만 채우고 mock은 None
    time_s: float | None = None
    # 실시간(live) 모드에서만 채운다. 화면이 보낸 프레임 번호, 그 프레임의 가로·세로(px). 박스 좌표의 기준 크기다
    frame: int | None = None
    frame_w_px: int | None = None
    frame_h_px: int | None = None
