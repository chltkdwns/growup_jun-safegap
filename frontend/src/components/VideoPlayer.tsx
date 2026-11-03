import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { VIDEO_SYNC_TOLERANCE_S } from '../constants'
import './VideoPlayer.css'

interface VideoPlayerProps {
  src?: string // 영상 파일 주소. 없으면 "영상 없음" 자리 표시만 보인다
  timeS?: number | null // 서버가 알려 준 현재 영상 위치(초). 있으면 영상을 이 위치에 맞춘다
  children?: ReactNode // 영상 위에 겹쳐 그릴 오버레이 (BoxOverlay 등)
}

/**
 * 16:9 영상 영역. 위에 박스·경고 오버레이를 children으로 겹쳐 그린다.
 * 사용처: App. src가 없으면 영상 자리 표시만 보여 준다(영상 파일이 생기면 src로 연결).
 */
export function VideoPlayer({ src, timeS, children }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)

  // 서버(박스)와 영상이 벌어지면 영상 위치를 서버에 맞춘다. 조금 벌어진 것은 건드리지 않는다
  useEffect(() => {
    const video = videoRef.current
    if (!video || timeS == null) return
    if (Math.abs(video.currentTime - timeS) > VIDEO_SYNC_TOLERANCE_S) video.currentTime = timeS
  }, [timeS])

  return (
    // 바깥 div가 16:9 틀이자 오버레이의 기준 위치(position: relative)다
    <div className="video-player">
      {/* 영상 파일이 있으면 <video>, 없으면 자리 표시. 서버 재생(replay)과 맞추려고 자동 반복 재생하고 컨트롤은 뺐다 */}
      {src ? <video ref={videoRef} src={src} autoPlay loop muted /> : <span className="video-empty">영상 없음</span>}
      {/* 오버레이는 영상 뒤에 렌더돼 영상 위에 겹친다 */}
      {children}
    </div>
  )
}
