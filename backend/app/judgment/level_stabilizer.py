from app.judgment.warning_level import LEVELS


class LevelStabilizer:
    """경고 단계가 프레임마다 바뀌어 화면이 깜빡이는 것을 막는다.

    사용처: B(판단) 단계. 앞차 한 대마다 객체 하나를 만들고, decide_level() 결과를 매 프레임 update()에 넣는다.
    입력: raw_level 이번 프레임의 경고 단계("정상"~"위험")
    출력: 화면에 보여 줄 경고 단계
    규칙: 더 위험한 쪽으로는 즉시 올리고, 덜 위험한 쪽으로는 hold_frames 프레임 연속 유지될 때만 내린다.
    주의: 앞차 ID가 바뀌면 reset()을 호출한다.
    """

    def __init__(self, hold_frames: int):
        self.hold_frames = hold_frames  # 내려가기 전에 기다릴 프레임 수 (config에서 받음)
        self.reset()

    def reset(self) -> None:
        self.shown = LEVELS[0]   # 지금 화면에 보이는 단계
        self.pending = None      # 내려가려고 기다리는 단계
        self.count = 0           # pending이 연속으로 나온 횟수

    def update(self, raw_level: str) -> str:
        raw_i, shown_i = LEVELS.index(raw_level), LEVELS.index(self.shown)
        # 1) 더 위험해지면 즉시 반영 (경고가 늦으면 안 되니까)
        if raw_i >= shown_i:
            self.shown, self.pending, self.count = raw_level, None, 0
            return self.shown
        # 2) 덜 위험해지면, 같은 단계가 연속으로 나오는지 센다
        if raw_level == self.pending:
            self.count += 1
        else:
            self.pending, self.count = raw_level, 1
        # 3) hold_frames 연속이면 그때 내림
        if self.count >= self.hold_frames:
            self.shown, self.pending, self.count = raw_level, None, 0
        return self.shown
