import { LEVELS } from '../constants'
import type { FrameResult } from '../hooks/useWebSocket'
import './WarningBadge.css'

/**
 * 경고 단계 배지(글자·색)와 영상 테두리를 그린다.
 * 사용처: App이 VideoPlayer의 children으로 넣는다.
 * 단계 판정은 서버가 보낸 frame.level을 그대로 쓴다. 프레임이 아직 없으면 그리지 않는다.
 */
export function WarningBadge({ frame }: { frame: FrameResult | null }) {
  // 1단계: 프레임이 없으면 그리지 않는다
  if (!frame) return null

  // 2단계: 단계에 맞는 글자와 색
  const { ko, en, color } = LEVELS[frame.level]

  return (
    <>
      {/* 3단계: 영상 테두리. CSS 변수로 색을 내려 단계가 바뀌면 같이 바뀐다 */}
      <div className="warning-border" style={{ '--level-color': color } as React.CSSProperties} />
      {/* 4단계: 오른쪽 위 단계 배지 */}
      <div className="warning-badge" style={{ background: color }}>
        <span className="warning-badge-ko">{ko}</span>
        <span className="warning-badge-en">{en}</span>
      </div>
    </>
  )
}
