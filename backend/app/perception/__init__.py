"""A(인식): 검출, 트래킹, 앞차 선정, 끼어들기 판단.

FastAPI를 import하지 않는 순수 함수만 둔다. 결과는 schemas.PerceptionResult로 내보낸다.
트래킹 결과는 프레임마다 {트래킹 ID: [x1, y1, x2, y2]} 딕셔너리로 주고받는다.
"""
