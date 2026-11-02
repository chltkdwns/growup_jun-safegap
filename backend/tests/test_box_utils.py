from app.judgment.box_utils import box_iou

def test_iou_same_box_is_1():
    assert box_iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0

def test_iou_no_overlap_is_0():
    assert box_iou([0, 0, 10, 10], [20, 0, 30, 10]) == 0.0

def test_iou_half_overlap():
    # 겹친 넓이 50, 합친 넓이 150 → 1/3
    assert abs(box_iou([0, 0, 10, 10], [5, 0, 15, 10]) - 1 / 3) < 1e-9