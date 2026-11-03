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

def resolve_focal_px(camera_cfg: dict, img_w_px: int) -> float:
    """카메라 설정과 실제 프레임 폭으로 이번 영상(연결)에 쓸 초점거리(px)를 정한다.

    사용처: FrameJudge를 만들기 직전에 한 번 호출한다.
            파일 방식은 영상을 열 때, 폰 방식은 첫 프레임의 frame_w_px를 받았을 때.
    입력: camera_cfg 설정의 camera 섹션 (focal_px 또는 hfov_deg), img_w_px 실제로 받은 프레임 가로 폭(px)
    출력: 초점거리(px)
    주의: focal_px를 직접 적었으면 그 값을 그대로 쓴다 (그 값을 잰 해상도와 같은 크기로 받아야 맞음).
          hfov_deg만 있으면 받은 폭으로 계산하므로, 폰이 1920px이 아닌 크기로 보내도 자동으로 맞는다.
    """
    if camera_cfg.get("focal_px"):
        return float(camera_cfg["focal_px"])
    if camera_cfg.get("hfov_deg"):
        return focal_px_from_hfov(img_w_px, camera_cfg["hfov_deg"])
    raise ValueError("camera 설정에 focal_px나 hfov_deg 중 하나는 있어야 해요")