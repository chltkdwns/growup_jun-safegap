"""
요약: schemas.py가 올바른 데이터는 통과시키고, 틀린 데이터는 막는지 확인한다.
사용처: pytest (backend 폴더에서 pytest 실행)
주의: 형식(필드·단위)을 바꾸면 이 테스트도 같이 고친다.
"""
import pytest
from pydantic import ValidationError

from app.schemas import JudgmentFrame, PerceptionFrame


def test_perception_ok():
    """정상: 앞차가 있는 A 출력이 그대로 통과하고, 값을 꺼낼 수 있다."""
    p = PerceptionFrame.model_validate(
        {"frame": 0, "time": 0.0, "lead": {"id": 3, "box": [1, 2, 3, 4]}, "cut_in": False}
    )
    assert p.lead.id == 3


def test_perception_no_lead():
    """정상: 앞차가 없으면 lead=None. cut_in은 안 보내도 기본값 False."""
    p = PerceptionFrame.model_validate({"frame": 1, "time": 0.1, "lead": None})
    assert p.lead is None
    assert p.cut_in is False


def test_bad_box_rejected():
    """오류: box 숫자가 4개가 아니면(여기선 3개) 막는다."""
    with pytest.raises(ValidationError):
        PerceptionFrame.model_validate({"frame": 0, "time": 0, "lead": {"id": 1, "box": [1, 2, 3]}})


def test_bad_level_rejected():
    """오류: level이 정해진 4개 한글 단계가 아니면(여기선 영어 "danger") 막는다."""
    with pytest.raises(ValidationError):
        JudgmentFrame.model_validate(
            {"frame": 0, "speed_kmh": 50, "distance_m": 10, "ttc_s": None, "level": "danger"}
        )