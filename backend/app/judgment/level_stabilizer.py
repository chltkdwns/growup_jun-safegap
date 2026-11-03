from app.judgment.warning_level import LEVELS


class LevelStabilizer:
    """경고 단계가 프레임마다 바뀌어 화면이 깜빡이는 것을 막는다.

    사용처: B(판단) 단계. 앞차 한 대마다 객체 하나를 만들고, decide_level() 결과를 매 프레임 update()에 넣는다.
    입력: raw_level 이번 프레임의 경고 단계("정상"~"위험")
    출력: 화면에 보여 줄 경고 단계
    규칙: 더 위험한 쪽으로는 즉시 올리고, 덜 위험한 쪽으로는 hold_frames 프레임 연속 유지될 때만 내린다.
    주의: 앞차 ID가 바뀌면 reset()을 호출한다.
    """

    def __init__(self, hold_s: float):
        self.hold_s = hold_s  # 내려가기 전에 기다릴 시간(초) (config에서 받음)
        self.reset()

    def reset(self) -> None:
        self.shown = LEVELS[0]     # 지금 화면에 보이는 단계
        self.pending = None        # 내려가려고 기다리는 단계
        self.pending_since = None  # pending이 처음 나온 시각(초)

    def update(self, raw_level: str, time_s: float) -> str:
        raw_i, shown_i = LEVELS.index(raw_level), LEVELS.index(self.shown)
        # 1) 더 위험해지면 즉시 반영 (경고가 늦으면 안 되니까)
        if raw_i >= shown_i:
            self.shown, self.pending, self.pending_since = raw_level, None, None
            return self.shown
        # 2) 덜 위험해지면, 그 단계가 언제부터 이어졌는지 기록
        if raw_level != self.pending:
            self.pending, self.pending_since = raw_level, time_s
        # 3) hold_s초 이상 이어졌으면 그때 내림
        if time_s - self.pending_since >= self.hold_s:
            self.shown, self.pending, self.pending_since = raw_level, None, None
        return self.shown
