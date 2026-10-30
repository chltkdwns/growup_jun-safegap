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
        self.ttc = TTCEstimator(fps, cfg_judgment["ttc_window_frames"], cfg_judgment["max_ttc_s"])
        self.stabilizer = LevelStabilizer(cfg_judgment["level_hold_frames"])
        self.lead_id = None   # 지금 따라가고 있는 앞차 ID

    def judge_frame(self, perception: dict, speed_kmh: float | None) -> dict:
        """한 프레임의 A→B 결과(perception)를 B→C 형식으로 바꾼다.

        입력: perception {"frame", "time", "lead": {"id", "box"} 또는 None, "cut_in"},
              speed_kmh 내 속도(km/h, 모르면 None)
        출력: {"frame", "speed_kmh", "distance_m", "ttc_s", "level"}
        """
        lead = perception["lead"]
        # 1) 앞차가 바뀌거나 사라지면 이전 차의 기록을 버림
        new_id = lead["id"] if lead else None
        if new_id != self.lead_id:
            self.ttc.reset()
            self.stabilizer.reset()
            self.lead_id = new_id

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

        return {
            "frame": perception["frame"],
            "speed_kmh": speed_kmh,
            "distance_m": None if distance_m is None else round(distance_m, 1),
            "ttc_s": None if ttc_s is None else round(float(ttc_s), 2),
            "level": level,
        }
