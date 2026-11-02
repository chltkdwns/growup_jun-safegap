from app.judgment.box_utils import box_iou
from app.judgment.distance import estimate_distance_m
from app.judgment.level_stabilizer import LevelStabilizer
from app.judgment.ttc import TTCEstimator
from app.judgment.warning_level import decide_level


class FrameJudge:
    """A의 프레임별 인식 결과와 내 속도로 B→C 판단 결과를 만든다.

    사용처: B(판단) 단계의 입구. 영상 하나마다 객체 하나를 만들고,
            C의 analyze 엔드포인트가 매 프레임 judge_frame()을 호출한다.
    입력: cfg_judgment config의 judgment 섹션, fps 영상 프레임 속도, focal_px 초점거리(px)
    주의: 앞차가 바뀌거나 사라지면 TTC와 깜빡임 방지 상태를 초기화한다.
    """

    def __init__(self, cfg_judgment: dict, fps: float, focal_px: float):
        self.cfg = cfg_judgment
        self.focal_px = focal_px
        window_frames = max(3, round(cfg_judgment["ttc_window_s"] * fps))  # 초 → 프레임 수
        self.ttc = TTCEstimator(fps, window_frames, cfg_judgment["max_ttc_s"])
        self.stabilizer = LevelStabilizer(cfg_judgment["level_hold_frames"])
        self.lead_id = None   # 지금 따라가고 있는 앞차 ID
        self.lead_box = None  # 직전 프레임의 앞차 박스 (id가 바뀌어도 같은 차인지 확인용)
        self.max_missing_frames = round(cfg_judgment["max_missing_s"] * fps)  # 앞차를 놓쳐도 버틸 프레임 수
        self.missing_frames = 0  # 지금까지 연속으로 앞차를 놓친 프레임 수
        self.last_out = None     # 마지막으로 앞차가 있었던 프레임의 결과

    def _is_same_car(self, new_id: int | None, new_box: list | None) -> bool:
        """이번 앞차가 직전 앞차와 같은 차인지 판단한다.

        사용처: judge_frame()에서 TTC를 리셋할지 정할 때.
        출력: id가 같거나, id가 달라도 박스가 많이 겹치면(IoU ≥ same_car_iou) True
        주의: 트래커가 같은 차에 id를 새로 붙이는 경우(id 스위칭) TTC가 끊기지 않게 하려는 것.
        """
        if new_id == self.lead_id:
            return True
        if new_box is None or self.lead_box is None:
            return False
        return box_iou(new_box, self.lead_box) >= self.cfg["same_car_iou"]

    def judge_frame(self, perception: dict, speed_kmh: float | None) -> dict:
        """한 프레임의 A→B 결과(perception)를 B→C 형식으로 바꾼다.

        입력: perception {"frame", "time", "lead": {"id", "box"} 또는 None, "cut_in"},
              speed_kmh 내 속도(km/h, 모르면 None)
        출력: {"frame", "speed_kmh", "distance_m", "ttc_s", "level"}
        """
        lead = perception["lead"]
        
        # 0) 앞차를 잠깐(max_missing_s 이내) 놓치면 직전 결과를 유지 (검출이 1~2프레임 끊기는 경우)
        if lead is None and self.last_out is not None and self.missing_frames < self.max_missing_frames:
            self.missing_frames += 1
            return dict(self.last_out, frame=perception["frame"], speed_kmh=speed_kmh)
        self.missing_frames = 0
        
        # 1) 앞차가 바뀌거나 사라지면 이전 차의 기록을 버림
        new_id = lead["id"] if lead else None
        new_box = lead["box"] if lead else None
        if not self._is_same_car(new_id, new_box):
            self.ttc.reset()
            self.stabilizer.reset()
        self.lead_id, self.lead_box = new_id, new_box

        # 2) 앞차가 있으면 거리와 TTC 계산
        distance_m = ttc_s = None
        if lead:
            x1, _, x2, _ = lead["box"]
            box_w_px = x2 - x1
            distance_m = estimate_distance_m(box_w_px, self.focal_px, self.cfg["car_width_m"])
            ttc_s = self.ttc.update(box_w_px)

        # 3) 경고 단계를 정하고 깜빡임을 막음
        raw_level = decide_level(
            distance_m, speed_kmh, ttc_s, perception["cut_in"],
            self.cfg["safe_gap_s"], self.cfg["ttc_warning_s"], self.cfg["ttc_danger_s"],
        )
        level = self.stabilizer.update(raw_level)

        out = {
            "frame": perception["frame"],
            "speed_kmh": speed_kmh,
            "distance_m": None if distance_m is None else round(distance_m, 1),
            "ttc_s": None if ttc_s is None else round(float(ttc_s), 2),
            "level": level,
        }
        self.last_out = out if lead else None  # 앞차가 있을 때만 "유지할 결과"로 기억
        return out
