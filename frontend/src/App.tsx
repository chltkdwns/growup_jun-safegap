import { BoxOverlay } from './components/BoxOverlay'
import { EventBanner } from './components/EventBanner'
import { InfoPanel } from './components/InfoPanel'
import { SoundToggle } from './components/SoundToggle'
import { SpeedInput } from './components/SpeedInput'
import { ThemeToggle } from './components/ThemeToggle'
import { VideoPlayer } from './components/VideoPlayer'
import { WarningBadge } from './components/WarningBadge'
import { useAlarmSound } from './hooks/useAlarmSound'
import { useTheme } from './hooks/useTheme'
import { useWebSocket } from './hooks/useWebSocket'
import './App.css'

// 화면 전체 조립. 서버에서 받은 frame을 아래 부품들에 내려 주는 역할만 한다.
// 배치(가로 화면은 영상 + 오른쪽 패널, 세로 화면은 위아래)는 App.css가 정한다.
function App() {
  // 서버(/ws)가 보내는 가장 최근 프레임과 연결 상태
  const { frame, connected, setSpeed } = useWebSocket()
  // 경고 단계가 올라갈 때만 소리를 낸다 (버튼으로 켠 경우에만)
  const { soundOn, toggleSound } = useAlarmSound(frame?.level)
  // 라이트/다크 선택 (시스템 설정을 따르는 것이 기본)
  const { mode, changeMode } = useTheme()

  return (
    <div className="app">
      <header className="app-header">
        <h1>SafeGap</h1>
        <span className="status" data-connected={connected}>
          {connected ? '연결됨' : '연결 안 됨'}
        </span>
      </header>

      <main className="app-main">
        {/* 영상 틀 위에 박스를 겹쳐 그린다. 경고 배지 등 다른 오버레이도 같은 자리에 children으로 추가한다 */}
        <section className="app-video">
          <VideoPlayer>
            <BoxOverlay frame={frame} />
            <WarningBadge frame={frame} />
            <EventBanner frame={frame} />
          </VideoPlayer>
        </section>

        <aside className="app-side">
          <InfoPanel frame={frame} />
          {/* 조작 묶음: 속도 슬라이더, 경고음, 테마. 세로 화면에서는 아래 고정 바가 된다 */}
          <div className="app-controls">
            {/* 슬라이더 값이 바뀌면 서버에 내 속도를 알린다 */}
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
