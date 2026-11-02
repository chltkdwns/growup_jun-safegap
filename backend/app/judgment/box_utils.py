def box_iou(box_a: list, box_b: list) -> float:
    """두 박스가 겹치는 정도(IoU, 0~1)를 구한다.

    사용처: judge.py에서 id가 바뀐 앞차가 같은 차인지 확인할 때.
    입력: box_a, box_b [x1, y1, x2, y2] 픽셀
    출력: 겹친 넓이 ÷ 합친 넓이. 안 겹치면 0, 완전히 같으면 1
    """
    ix1, iy1 = max(box_a[0], box_b[0]), max(box_a[1], box_b[1])
    ix2, iy2 = min(box_a[2], box_b[2]), min(box_a[3], box_b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0