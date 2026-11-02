"""프레임마다 내 차선 좌우 경계를 찾아 사다리꼴을 따라가게 한다."""

import numpy as np

from app.perception.lane_calib import find_lane_segments, toward_vp_mask

# 프레임 하나에서는 차선 조각이 적어서 영상 단위 보정(1.5도)보다 넉넉하게 본다
LANE_TOL_DEG = 3.0


def edges_at_y(segments: np.ndarray, vp_px: tuple[float, float], y_px: float) -> np.ndarray:
    """차선 조각을 소실점까지 이은 직선이 높이 y_px에서 지나는 x를 구한다.

    사용처: LaneTracker.update()가 후보 차선의 아래 끝 위치를 잴 때 호출한다.
    입력: segments (N, 4) 소실점을 향하는 직선 조각 (px), vp_px 소실점 (px), y_px 높이 (px)
    출력: (N,) x 좌표 배열 (px)
    """
    vp_x, vp_y = vp_px
    mid_x = (segments[:, 0] + segments[:, 2]) / 2
    mid_y = (segments[:, 1] + segments[:, 3]) / 2
    # 소실점과 조각 가운데를 잇는 직선을 y_px까지 연장한다
    return vp_x + (mid_x - vp_x) * (y_px - vp_y) / (mid_y - vp_y)


class LaneTracker:
    """내 차선 좌우 경계의 아래 끝 x를 프레임마다 갱신하고 EMA로 부드럽게 한다.

    직전 프레임의 경계 위치를 기억해야 해서 클래스로 만들었다.
    """

    def __init__(
        self,
        trapezoid_px: np.ndarray,
        vp_px: tuple[float, float],
        frame_w_px: int,
        perception_cfg: dict,
    ) -> None:
        """사용처: pipeline.analyze_video()가 영상 하나에 한 번 만든다.

        입력: trapezoid_px 영상 단위로 정한 첫 사다리꼴 (px), vp_px 소실점 (px),
              frame_w_px 프레임 너비 (px), perception_cfg config의 perception 섹션
        """
        self.vp_px = vp_px
        self.top_y_px = float(trapezoid_px[0, 1])
        self.bottom_y_px = float(trapezoid_px[2, 1])
        # 시작 위치는 영상 단위 사다리꼴의 아래 변 양 끝
        self.left_x_px = float(trapezoid_px[3, 0])
        self.right_x_px = float(trapezoid_px[2, 0])
        self.alpha = perception_cfg["lane_ema_alpha"]
        self.min_w_px = frame_w_px * perception_cfg["lane_width_min_ratio"]
        self.max_w_px = frame_w_px * perception_cfg["lane_width_max_ratio"]

    def update(self, frame: np.ndarray) -> np.ndarray:
        """이번 프레임의 차선을 찾아 경계를 갱신하고 사다리꼴을 돌려준다.

        사용처: A(인식) 단계. pipeline.analyze_video()가 매 프레임 호출한다.
        입력: frame (H, W, 3) BGR 원본 이미지
        출력: (4, 2) float32 사다리꼴 (px). 왼쪽 위 → 오른쪽 위 → 오른쪽 아래 → 왼쪽 아래
        주의: 차선이 안 보이는 프레임은 직전 위치를 그대로 쓴다.
              소실점은 영상 단위 값을 고정해서 쓰므로 급커브에서는 어긋난다.
        """
        segs = find_lane_segments(frame)
        # 소실점을 향하고 본넷 위에 있는 조각만 차선으로 본다
        if len(segs):
            above_hood = np.minimum(segs[:, 1], segs[:, 3]) < self.bottom_y_px
            segs = segs[above_hood & toward_vp_mask(segs, self.vp_px, LANE_TOL_DEG)]
        if len(segs):
            xs = edges_at_y(segs, self.vp_px, self.bottom_y_px)
            center_x = (self.left_x_px + self.right_x_px) / 2
            left_xs, right_xs = xs[xs < center_x], xs[xs >= center_x]
            # 직전 경계에 가장 가까운 선을 고른다 (도로 화살표·옆 차선에 덜 끌려가게)
            new_left = (
                left_xs[np.argmin(np.abs(left_xs - self.left_x_px))]
                if len(left_xs)
                else self.left_x_px
            )
            new_right = (
                right_xs[np.argmin(np.abs(right_xs - self.right_x_px))]
                if len(right_xs)
                else self.right_x_px
            )
            # 차선 폭이 말이 안 되면 잘못 찾은 것으로 보고 이번 프레임은 건너뛴다
            if self.min_w_px <= new_right - new_left <= self.max_w_px:
                self.left_x_px += self.alpha * (new_left - self.left_x_px)
                self.right_x_px += self.alpha * (new_right - self.right_x_px)
        return self.trapezoid_px()

    def trapezoid_px(self) -> np.ndarray:
        """현재 좌우 경계로 사다리꼴을 만든다.

        사용처: update()가 마지막에 호출한다.
        출력: (4, 2) float32 사다리꼴 (px)
        """
        vp_x, vp_y = self.vp_px
        # 위 변 꼭짓점은 아래 끝과 소실점을 잇는 직선 위에 둔다
        shrink = (self.top_y_px - vp_y) / (self.bottom_y_px - vp_y)
        top_left = vp_x + (self.left_x_px - vp_x) * shrink
        top_right = vp_x + (self.right_x_px - vp_x) * shrink
        return np.array(
            [
                [top_left, self.top_y_px],
                [top_right, self.top_y_px],
                [self.right_x_px, self.bottom_y_px],
                [self.left_x_px, self.bottom_y_px],
            ],
            dtype=np.float32,
        )
