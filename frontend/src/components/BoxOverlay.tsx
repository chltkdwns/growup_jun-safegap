import { FRAME_H_PX, FRAME_W_PX, LEVELS } from '../constants'
import type { FrameResult } from '../hooks/useWebSocket'

// 아래 값은 모두 FRAME_W_PX x FRAME_H_PX 좌표계의 px (화면이 줄면 같이 줄어든다)
const LABEL_FONT_PX = 30 // 라벨 글자 크기
const LABEL_H_PX = 44 // 라벨 배경 높이
const LABEL_PAD_PX = 12 // 라벨 글자 좌우 여백
const BOX_LINE_PX = 4 // 박스 테두리 두께

/**
 * 앞차 박스와 "앞차 41.2m" 라벨을 영상 위에 그린다.
 * 사용처: App이 VideoPlayer의 children으로 넣는다.
 * 앞차가 없으면(lead_box_px가 null) 아무것도 그리지 않는다.
 */
export function BoxOverlay({ frame }: { frame: FrameResult | null }) {
  // 1단계: 아직 프레임이 없거나 앞차가 없으면 그리지 않는다
  if (!frame || !frame.lead_box_px || frame.distance_m === null) return null

  // 2단계: 박스 좌표, 색, 라벨 글자와 배경 폭 준비
  const [x1, y1, x2, y2] = frame.lead_box_px
  const color = LEVELS[frame.level].color // 박스 색은 경고 단계를 따른다
  const label = `앞차 ${frame.distance_m.toFixed(1)}m`
  // 글자 폭은 정확히 잴 수 없어 글자 수 x 글자 크기 x 0.62로 어림한다 (한글·숫자 혼합 기준)
  const labelW = label.length * LABEL_FONT_PX * 0.62 + LABEL_PAD_PX * 2

  return (
    // viewBox를 서버 좌표계와 같게 두면 영상이 커지거나 작아져도 박스가 같이 따라간다
    <svg
      viewBox={`0 0 ${FRAME_W_PX} ${FRAME_H_PX}`}
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
    >
      {/* 3단계: 박스 테두리 */}
      <rect x={x1} y={y1} width={x2 - x1} height={y2 - y1} fill="none" stroke={color} strokeWidth={BOX_LINE_PX} />
      {/* 4단계: 박스 위쪽에 거리 라벨 (배경 + 글자) */}
      <rect x={x1} y={y1 - LABEL_H_PX} width={labelW} height={LABEL_H_PX} fill={color} />
      <text
        x={x1 + LABEL_PAD_PX}
        y={y1 - LABEL_H_PX / 2}
        fill="#0a0d12"
        fontSize={LABEL_FONT_PX}
        fontWeight={600}
        dominantBaseline="middle"
      >
        {label}
      </text>
    </svg>
  )
}
