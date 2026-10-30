import math


def focal_px_from_hfov(img_w_px: int, hfov_deg: float) -> float:
    """화면 폭과 수평 화각으로 초점거리(px)를 구한다.

    사용처: B(판단) 단계. 영상을 처음 열 때 한 번 호출해 focal_px를 정한다.
    입력: img_w_px 영상 가로 해상도(px), hfov_deg 카메라 수평 화각(도, config)
    출력: 초점거리(px)
    주의: config에 focal_px가 이미 있으면 이 함수 대신 그 값을 쓴다.
    """
    # 화면 절반 폭 ÷ tan(화각 절반) = 초점거리
    return (img_w_px / 2) / math.tan(math.radians(hfov_deg) / 2)


def estimate_distance_m(box_w_px: float, focal_px: float, car_w_m: float) -> float:
    """앞차 박스 폭으로 앞차까지의 거리(m)를 구한다.

    사용처: B(판단) 단계. 매 프레임 앞차에 대해 호출해 안전거리 판단에 쓴다.
    입력: box_w_px 앞차 박스 폭(px), focal_px 초점거리(px), car_w_m 가정 차폭(m, config)
    출력: 거리(m)
    주의: 차폭이 1.8m와 크게 다른 트럭·경차, 화면 가장자리에서 잘린 박스는 오차가 크다.
    """
    # 핀홀 공식: 거리 = 초점거리 × 실제 폭 ÷ 화면 속 폭
    return focal_px * car_w_m / box_w_px
