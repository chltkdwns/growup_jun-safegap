import type { FrameResult } from '../hooks/useWebSocket'
import './SpeedDisplay.css'

/**
 * 내 속도를 큰 숫자로 보여 준다 (세로 화면 맨 위, 계기판처럼).
 * 사용처: App이 영상 위에 둔다. 가로 화면에서는 CSS가 숨긴다(SpeedDisplay.css 참고).
 * 값은 서버가 보낸 frame.speed_kmh이다. 프레임이 아직 없으면 "—".
 */
export function SpeedDisplay({ frame }: { frame: FrameResult | null }) {
  return (
    <div className="speed-display">
      <b>{frame && frame.speed_kmh !== null ? frame.speed_kmh.toFixed(0) : '—'}</b>
      <span>KM/H</span>
    </div>
  )
}
