import type { ReactNode } from 'react'
import './VideoPlayer.css'

interface VideoPlayerProps {
  src?: string // 영상 파일 주소. 없으면 "영상 없음" 자리 표시만 보인다
  children?: ReactNode // 영상 위에 겹쳐 그릴 오버레이 (BoxOverlay 등)
}

/**
 * 16:9 영상 영역. 위에 박스·경고 오버레이를 children으로 겹쳐 그린다.
 * 사용처: App. src가 없으면 영상 자리 표시만 보여 준다(영상 파일이 생기면 src로 연결).
 */
export function VideoPlayer({ src, children }: VideoPlayerProps) {
  return (
    // 바깥 div가 16:9 틀이자 오버레이의 기준 위치(position: relative)다
    <div className="video-player">
      {/* 영상 파일이 있으면 <video>, 없으면 자리 표시 */}
      {src ? <video src={src} controls muted /> : <span className="video-empty">영상 없음</span>}
      {/* 오버레이는 영상 뒤에 렌더돼 영상 위에 겹친다 */}
      {children}
    </div>
  )
}
