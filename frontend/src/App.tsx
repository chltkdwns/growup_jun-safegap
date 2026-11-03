import logo from './assets/logo.png'
import { BoxOverlay } from './components/BoxOverlay'
import { EventBanner } from './components/EventBanner'
import { InfoPanel } from './components/InfoPanel'
import { SoundToggle } from './components/SoundToggle'
import { SpeedDisplay } from './components/SpeedDisplay'
import { SpeedInput } from './components/SpeedInput'
import { ThemeMenu } from './components/ThemeMenu'
import { ThemeToggle } from './components/ThemeToggle'
import { VideoPlayer } from './components/VideoPlayer'
import { WarningBadge } from './components/WarningBadge'
import { useAlarmSound } from './hooks/useAlarmSound'
import { useCameraStream } from './hooks/useCameraStream'
import { useTheme } from './hooks/useTheme'
import { liveWsUrl, useWebSocket } from './hooks/useWebSocket'
import './App.css'

// 화면 전체 조립. 서버에서 받은 frame을 아래 부품들에 내려 주는 역할만 한다.
// 배치(가로 화면은 영상 + 오른쪽 패널, 세로 화면은 위아래)는 App.css가 정한다.
function App() {
  // 주소에 ?live 가 있으면 실시간 모드: 카메라 프레임을 서버로 보내 분석한다 (없으면 mock·재생 모드)
  const live = new URLSearchParams(window.location.search).has('live')
  // 서버(/ws)가 보내는 가장 최근 프레임과 연결 상태
  const { frame, connected, setSpeed, sendFrame } = useWebSocket(live ? liveWsUrl() : undefined)
  // 실시간 모드의 카메라 영상과 오류, 서버 왕복 시간
  const { stream, error: cameraError, roundTrip } = useCameraStream(live, sendFrame, frame?.frame)
  // 경고 단계가 올라갈 때만 소리를 낸다 (버튼으로 켠 경우에만)
  const { soundOn, toggleSound } = useAlarmSound(frame?.level)
  // 라이트/다크 선택 (시스템 설정을 따르는 것이 기본)
  const { mode, changeMode } = useTheme()

  return (
    <div className="app">
      <header className="app-header">
        {/* 로고 이미지. 글자는 alt로 남겨 이미지가 안 뜰 때나 스크린리더에서 읽히게 한다 */}
        <h1 className="app-logo">
          <img src={logo} alt="SafeGap" />
        </h1>
        <div className="app-header-right">
          {/* 실시간 모드: 카메라 오류, 서버 왕복 시간(p50/p95)을 같이 보여 준다 */}
          {live && cameraError && <span className="status">{cameraError}</span>}
          {live && roundTrip && (
            <span className="status" title="서버 왕복 지연(p50/p95)">
              {roundTrip.p50.toFixed(0)}/{roundTrip.p95.toFixed(0)}ms
            </span>
          )}
          <span className="status" data-connected={connected}>
            <span className="status-text">{connected ? '연결됨' : '연결 안 됨'}</span>
          </span>
          {/* 세로 화면에서만 보이는 햄버거. 안에 화면 모드(테마) 선택이 들어 있다 */}
          <ThemeMenu mode={mode} onChange={changeMode} />
        </div>
      </header>

      <main className="app-main">
        {/* 영상 틀 위에 박스를 겹쳐 그린다. 경고 배지 등 다른 오버레이도 같은 자리에 children으로 추가한다 */}
        <section className="app-video">
          {/* 세로 화면에서만 보이는 큰 속도 숫자 (영상과 함께 위에 붙는다) */}
          <SpeedDisplay frame={frame} />
          <VideoPlayer src={live ? undefined : import.meta.env.VITE_VIDEO_SRC} stream={stream} fill={live} timeS={frame?.time_s}>
            <BoxOverlay frame={frame} />
            <WarningBadge frame={frame} />
            <EventBanner frame={frame} />
          </VideoPlayer>
        </section>

        <aside className="app-side">
          <InfoPanel frame={frame} />
          {/* 조작 묶음: 속도 슬라이더, 경고음, 테마. 세로 화면에서는 아래 고정 바가 된다 */}
          <div className="app-controls">
            {/* 속도 요약 줄을 누르면 슬라이더가 펼쳐진다. 값이 바뀌면 서버에 내 속도를 알린다 */}
            <SpeedInput onChange={setSpeed} />
            <div className="app-toggles">
              <SoundToggle soundOn={soundOn} onToggle={toggleSound} />
              <ThemeToggle mode={mode} onChange={changeMode} />
            </div>
          </div>
        </aside>
      </main>
    </div>
  )
}

export default App
