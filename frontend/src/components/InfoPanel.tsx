import { LEVELS, MS_TO_KMH } from '../constants'
import type { FrameResult } from '../hooks/useWebSocket'
import './InfoPanel.css'

/**
 * 앞차 거리, 상대 속도, TTC, 안전거리 네 칸을 보여 준다.
 * 사용처: App이 영상 아래(또는 옆)에 둔다.
 * 프레임이 아직 없으면 모든 칸에 "—"를 보여 준다. TTC가 null이면 "다가오지 않음"이다.
 */
export function InfoPanel({ frame }: { frame: FrameResult | null }) {
  // 1단계: 칸에 보여 줄 글자 준비 (값이 없으면 "—")
  const distance = frame && frame.distance_m !== null ? frame.distance_m.toFixed(1) : '—'
  const relSpeed = frame ? (frame.rel_speed_mps * MS_TO_KMH).toFixed(0) : '—'
  const ttc = frame && frame.ttc_s !== null ? frame.ttc_s.toFixed(1) : '—'
  const safeDistance = frame && frame.safe_distance_m !== null ? frame.safe_distance_m.toFixed(1) : '—'

  // 2단계: 단계 색 (경고·위험일 때 TTC 숫자에 단계 색을 입힌다)
  const level = frame ? LEVELS[frame.level] : null
  const ttcHot = frame?.level === '경고' || frame?.level === '위험'

  return (
    <div className="info-panel">
      <Metric label="앞차 거리" value={distance} unit="m" />
      <Metric label="상대 속도" value={relSpeed} unit="km/h" sub={frame && frame.rel_speed_mps > 0 ? '가까워지는 중' : undefined} />
      <Metric
        label="TTC"
        value={ttc}
        unit="초"
        color={ttcHot ? level?.color : undefined}
        sub={frame && frame.ttc_s === null ? '다가오지 않음' : undefined}
      />
      <Metric label="안전거리" value={safeDistance} unit="m" sub="내 속도 × 2초" />
    </div>
  )
}

interface MetricProps {
  label: string
  value: string
  unit: string
  color?: string // 값 글자색. 없으면 기본색
  sub?: string // 값 아래 작은 보조 설명
}

// 칸 하나: 이름, 큰 숫자 + 단위, 보조 설명
function Metric({ label, value, unit, color, sub }: MetricProps) {
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className="metric-num">
        <b style={color ? { color } : undefined}>{value}</b>
        <em>{unit}</em>
      </div>
      <div className="metric-sub">{sub ?? ' '}</div>
    </div>
  )
}
