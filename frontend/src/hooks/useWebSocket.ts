import { useCallback, useEffect, useRef, useState } from 'react'
import type { EventType, Level } from '../constants'

// 백엔드 schemas.py의 FrameResult와 같은 모양. 필드가 늘면 양쪽을 같이 고친다.
export interface FrameResult {
  distance_m: number | null // 앞차까지 거리(m). 앞차가 없으면 null
  // 앞차 박스 [x1, y1, x2, y2] (px, FRAME_W_PX x FRAME_H_PX 기준). 앞차가 없으면 null
  lead_box_px: [number, number, number, number] | null
  speed_kmh: number // 내 속도(km/h)
  rel_speed_mps: number // 앞차와 가까워지는 속도(m/s). 멀어지면 음수
  ttc_s: number | null // 충돌까지 남은 시간(초). 가까워지지 않으면 null
  safe_distance_m: number // 안전거리(m)
  level: Level // 경고 단계 (서버가 판정)
  event: EventType | null // 경고가 나온 이유. 단계가 safe이면 null
  time_s: number | null // 이 프레임의 영상 위치(초). 재생 모드에서만 값이 있다
}

// .env의 VITE_WS_URL이 없을 때 쓰는 기본 주소 (로컬 개발용)
const DEFAULT_WS_URL = 'ws://localhost:8000/ws'

/**
 * 분석 서버의 /ws에 연결해 가장 최근 프레임 결과를 돌려준다.
 * 사용처: App이 호출해 화면 컴포넌트에 frame을 내려 준다.
 * 아직 받은 프레임이 없으면 frame은 null이다.
 * setSpeed(km/h)는 서버로 내 속도 변경(set_speed)을 보낸다. 연결이 열려 있지 않으면 보내지 않는다.
 * 주의: 연결이 끊겨도 자동 재연결은 하지 않는다. 서버를 다시 켜면 페이지를 새로고침해야 한다.
 */
export function useWebSocket(url: string = import.meta.env.VITE_WS_URL ?? DEFAULT_WS_URL) {
  // 가장 최근 프레임 하나만 들고 있다 (프레임마다 화면을 다시 그린다)
  const [frame, setFrame] = useState<FrameResult | null>(null)
  const [connected, setConnected] = useState(false)
  // 보내기용으로 연결 객체를 들고 있는다 (바뀌어도 화면을 다시 그릴 필요는 없다)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    // 마운트 때 연결하고, 언마운트 때 닫는다
    const ws = new WebSocket(url)
    wsRef.current = ws
    // 연결 상태 표시 갱신
    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    // 서버가 보낸 JSON 문자열을 FrameResult로 바꿔 저장 (모양은 schemas.py와 같아야 한다)
    ws.onmessage = (event) => setFrame(JSON.parse(event.data) as FrameResult)
    return () => ws.close()
  }, [url])

  // 내 속도 변경 요청. 모양은 백엔드 schemas.py의 SetSpeed와 같아야 한다
  const setSpeed = useCallback((speedKmh: number) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'set_speed', speed_kmh: speedKmh }))
    }
  }, [])

  return { frame, connected, setSpeed }
}
