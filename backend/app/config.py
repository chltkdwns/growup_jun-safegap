from pathlib import Path

import yaml

# backend/config.yaml (이 파일 기준 경로라서 어디서 실행해도 같은 파일을 읽음)
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """config.yaml을 읽어 딕셔너리로 돌려준다.

    사용처: 전체. 서버 시작 시 C의 main.py가 한 번 호출하고, 테스트에서도 같은 값을 쓰려고 호출한다.
    입력: path 설정 파일 경로 (기본값: backend/config.yaml)
    출력: 설정 딕셔너리 (예: cfg["judgment"]["ttc_warning_s"])
    """
    with open(path, encoding="utf-8") as f:   # 한글 주석 때문에 utf-8 지정 (Windows 기본값 대비)
        return yaml.safe_load(f)
