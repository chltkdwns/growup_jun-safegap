"""역할 사이에 주고받는 데이터 형식 (공통 인터페이스).

이 파일을 바꾸면 세 명 모두에게 먼저 알리고, 영향받는 함수와 테스트를 같이 고친다.
필드 이름은 작업 프로세스 문서의 JSON 약속을 그대로 따른다.
"""

from typing import Literal

from pydantic import BaseModel


class LeadVehicle(BaseModel):
    """앞차 한 대의 트래킹 ID와 박스."""

    id: int  # ByteTrack이 붙인 트래킹 ID
    box: list[float]  # [x1, y1, x2, y2] (px, 원본 프레임 기준)


class PerceptionResult(BaseModel):
    """A → B: 한 프레임의 인식 결과."""

    frame: int  # 프레임 번호 (0부터)
    time: float  # 영상 시작부터의 시간 (s)
    lead: LeadVehicle | None  # 앞차, 없으면 None
    cut_in: bool  # 이 프레임에서 끼어들기가 감지됐는지


class JudgmentResult(BaseModel):
    """B → C: 한 프레임의 판단 결과."""

    frame: int
    speed_kmh: float
    distance_m: float | None  # 앞차가 없으면 None
    ttc_s: float | None  # 앞차가 없거나 가까워지지 않으면 None
    level: Literal["정상", "주의", "경고", "위험"]
