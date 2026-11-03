"""앞차가 화면 정면에서 옆으로 얼마나 떨어져 있는지 계산 (사다리꼴 대신 쓴다)."""


def lateral_offset_m(box: list[float], center_x_px: float, car_width_m: float) -> float:
    """박스 가운데가 화면 정면(center_x_px)에서 옆으로 몇 m 떨어져 있는지 구한다.

    사용처: lead.select_lead(), cut_in.CutInDetector.update(), debug.draw_debug()가 호출한다.
    입력: box [x1, y1, x2, y2] (px), center_x_px 내 차가 향하는 정면의 x (px),
          car_width_m 가정 차폭 (m, config의 car_width_m)
    출력: 옆 거리 (m). 오른쪽이면 양수, 왼쪽이면 음수
    주의: 차폭이 1.8m와 다른 트럭·경차는 오차가 크다. 화면 끝에서 잘린 박스는 폭이 줄어
          값이 믿을 수 없다.
    """
    box_w_px = box[2] - box[0]
    box_center_x_px = (box[0] + box[2]) / 2
    # 핀홀 공식을 옆 방향에 쓰면 초점거리가 약분돼서 "픽셀 차이 × 실제 폭 ÷ 박스 폭"만 남는다
    return (box_center_x_px - center_x_px) * car_width_m / box_w_px
