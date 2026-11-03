import { useEffect, useRef, useState } from 'react'
import { LIVE_FPS, LIVE_JPEG_QUALITY, LIVE_SEND_LONG_PX } from '../constants'

// 서버로 보낸 프레임이 결과로 돌아오는 데 걸린 시간(ms)의 중앙값(p50)과 95번째 백분위(p95)
export interface RoundTrip {
  p50: number
  p95: number
}

// 프레임 메시지 = 앞 4바이트 프레임 번호 + 4바이트 촬영 시각(ms) + JPEG. 서버 main.py의 FRAME_HEADER_BYTES와 같아야 한다
const FRAME_INDEX_BYTES = 4
const FRAME_HEADER_BYTES = 8
const RTT_WINDOW = 100 // 왕복 시간을 이만큼(개) 모아 백분위를 구한다
const RTT_REPORT_EVERY = 15 // 결과가 이 개수만큼 올 때마다 백분위를 갱신한다 (화면을 너무 자주 다시 그리지 않으려고)
const PENDING_LIMIT = 200 // 결과를 못 받은 보낸 기록을 이만큼만 들고 있는다 (서버가 프레임을 버리면 쌓이므로)

/** 정렬된 숫자 배열에서 q(0~1) 위치의 값을 고른다. */
function percentile(sorted: number[], q: number): number {
  return sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))]
}

/**
 * 카메라를 켜고, 일정 간격으로 프레임을 JPEG로 만들어 서버에 보낸다.
 * 사용처: App이 실시간(live) 모드일 때 호출한다. 돌려준 stream을 VideoPlayer가 화면에 보여 준다.
 * 입력: enabled 켜져 있을 때만 카메라를 쓴다, sendFrame 서버로 프레임을 보내는 함수(useWebSocket),
 *       resultFrame 서버가 마지막으로 결과를 돌려준 프레임 번호 (왕복 시간 계산용)
 * 출력: stream 카메라 영상, error 카메라를 못 켠 이유(없으면 null), roundTrip 왕복 시간 p50·p95
 * 주의: 폰에서는 HTTPS 주소(또는 localhost)에서만 카메라가 켜진다. 처리가 밀리면 보내기를 건너뛰어 지연이 쌓이지 않게 한다.
 */
export function useCameraStream(
  enabled: boolean,
  sendFrame: (data: ArrayBuffer) => boolean,
  resultFrame: number | null | undefined,
) {
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [roundTrip, setRoundTrip] = useState<RoundTrip | null>(null)
  // 프레임 번호 → 보낸 시각(ms). 결과가 돌아오면 차이로 왕복 시간을 구한다
  const sentAtRef = useRef(new Map<number, number>())
  const rttsRef = useRef<number[]>([])
  const resultCountRef = useRef(0)
  // effect를 다시 시작하지 않고도 최신 sendFrame을 쓰려고 ref에 담아 둔다
  const sendFrameRef = useRef(sendFrame)
  useEffect(() => {
    sendFrameRef.current = sendFrame
  }, [sendFrame])

  // 1단계: 카메라 켜기 (뒤쪽 카메라 우선). 끄거나 화면을 떠나면 카메라를 끈다
  useEffect(() => {
    if (!enabled) return
    let cancelled = false
    let opened: MediaStream | null = null
    // 카메라 기능이 없으면(HTTP 주소 등) 요청 대신 실패로 처리해 아래 catch에서 같이 안내한다
    const request = navigator.mediaDevices
      ? navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
      : Promise.reject(new DOMException('', 'NotSupportedError'))
    request
      .then((s) => {
        if (cancelled) return s.getTracks().forEach((t) => t.stop())
        opened = s
        setStream(s)
        setError(null)
      })
      .catch((e: Error) =>
        setError(
          e.name === 'NotAllowedError'
            ? '카메라 권한이 거부됐어요'
            : e.name === 'NotSupportedError'
              ? '이 주소에서는 카메라를 쓸 수 없어요 (HTTPS 필요)'
              : '카메라를 켤 수 없어요',
        ),
      )
    return () => {
      cancelled = true
      opened?.getTracks().forEach((t) => t.stop())
      setStream(null)
    }
  }, [enabled])

  // 2단계: 카메라가 켜지면 일정 간격으로 프레임을 잘라 JPEG로 보낸다
  useEffect(() => {
    if (!stream) return
    // 화면에 보이는 video와 따로, 캡처 전용 video를 하나 더 만든다 (같은 stream을 공유)
    const video = document.createElement('video')
    video.muted = true
    video.playsInline = true
    video.srcObject = stream
    void video.play()
    const canvas = document.createElement('canvas')
    const sentAt = sentAtRef.current
    let frameIdx = 0
    const startedMs = performance.now() // 촬영 시각은 카메라를 켠 뒤 지난 시간(ms)으로 보낸다
    let inFlight = false // 이전 프레임을 아직 만드는 중이면 건너뛴다

    const timer = setInterval(() => {
      if (inFlight || video.videoWidth === 0) return
      // 보낼 크기로 줄여 그린다 (원본 그대로 보내면 업로드가 너무 커진다). 긴 변을 항상 같은 길이로 맞춘다
      const scale = LIVE_SEND_LONG_PX / Math.max(video.videoWidth, video.videoHeight)
      canvas.width = Math.round(video.videoWidth * scale)
      canvas.height = Math.round(video.videoHeight * scale)
      canvas.getContext('2d')?.drawImage(video, 0, 0, canvas.width, canvas.height)
      const capturedMs = Math.round(performance.now() - startedMs) // 이 프레임을 찍은 시각
      inFlight = true
      canvas.toBlob(
        async (blob) => {
          try {
            if (!blob) return
            // 메시지 = 프레임 번호 + 촬영 시각(ms) + JPEG
            const jpeg = await blob.arrayBuffer()
            const message = new Uint8Array(FRAME_HEADER_BYTES + jpeg.byteLength)
            const header = new DataView(message.buffer)
            header.setUint32(0, frameIdx)
            header.setUint32(FRAME_INDEX_BYTES, capturedMs)
            message.set(new Uint8Array(jpeg), FRAME_HEADER_BYTES)
            if (sendFrameRef.current(message.buffer)) {
              sentAt.set(frameIdx, performance.now())
              if (sentAt.size > PENDING_LIMIT) sentAt.delete(sentAt.keys().next().value as number)
            }
            frameIdx += 1
          } finally {
            inFlight = false
          }
        },
        'image/jpeg',
        LIVE_JPEG_QUALITY,
      )
    }, 1000 / LIVE_FPS)

    return () => {
      clearInterval(timer)
      video.srcObject = null
      sentAt.clear()
    }
  }, [stream])

  // 3단계: 결과가 돌아올 때마다 왕복 시간을 모아 p50·p95를 갱신한다
  useEffect(() => {
    if (resultFrame == null) return
    const sentAt = sentAtRef.current.get(resultFrame)
    if (sentAt === undefined) return
    sentAtRef.current.delete(resultFrame)
    const rtts = rttsRef.current
    rtts.push(performance.now() - sentAt)
    if (rtts.length > RTT_WINDOW) rtts.shift()
    resultCountRef.current += 1
    if (resultCountRef.current % RTT_REPORT_EVERY === 0) {
      const sorted = [...rtts].sort((a, b) => a - b)
      setRoundTrip({ p50: percentile(sorted, 0.5), p95: percentile(sorted, 0.95) })
    }
  }, [resultFrame])

  return { stream, error, roundTrip }
}
