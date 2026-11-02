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