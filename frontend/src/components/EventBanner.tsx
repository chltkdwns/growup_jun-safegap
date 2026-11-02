import { EVENTS, EVENT_HOLD_MS, LEVELS } from '../constants'
import type { FrameResult } from '../hooks/useWebSocket'
import { useHeldValue } from '../hooks/useHeldValue'
import './EventBanner.css'

/**
 * 지금 경고가 나온 이유(안전거리 부족 / 끼어들기 / 급정거)를 영상 왼쪽 위에 문구로 알린다.
 * 사용처: App이 VideoPlayer의 children으로 넣는다.
 * 문구는 최소 EVENT_HOLD_MS(2초) 유지해서 순간적으로 스쳐 지나가도 읽을 수 있게 한다.
 */
export function EventBanner({ frame }: { frame: FrameResult | null }) {
  // 1단계: 서버가 보낸 상황을 최소 2초 붙잡아 둔다 (없으면 null)
  const event = useHeldValue(frame?.event ?? null, EVENT_HOLD_MS)
  if (!event) return null

  // 2단계: 색은 지금 단계를 따른다. 단계가 안전으로 내려가 문구만 남은 동안은 주의색으로 둔다
  const color = LEVELS[frame && frame.level !== 'safe' ? frame.level : 'caution'].color

  return (
    <div className="event-banner" style={{ color, borderColor: color }}>
      {EVENTS[event]}
    </div>
  )
}
