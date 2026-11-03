import { useEffect, useState } from 'react'
import { DEFAULT_SPEED_KMH, SPEED_MAX_KMH, SPEED_MIN_KMH, SPEED_STEP_KMH } from '../constants'
import { GPS_STALE_MS, useGpsSpeed } from '../hooks/useGpsSpeed'
import type { GpsStatus } from '../hooks/useGpsSpeed'
import './SpeedInput.css'

// GPS를 켰지만 값이 아직 없을 때 보여 줄 안내. 이때는 슬라이더 값이 대신 쓰인다
const GPS_NOTES: Record<GpsStatus, string> = {
  waiting: 'GPS 신호를 기다리는 중이에요. 그동안 슬라이더 값을 써요.',
  ok: 'GPS가 속도를 알려 주지 않아요. 슬라이더 값을 써요.',
  denied: '위치 권한이 꺼져 있어요. 슬라이더 값을 써요.',
  unavailable: '이 기기나 주소에서는 GPS를 쓸 수 없어요. 슬라이더 값을 써요.',
  stale: 'GPS 신호를 기다리는 중이에요. 그동안 슬라이더 값을 써요. 신호가 돌아오면 다시 GPS를 써요.',
}

/**
 * 내 속도를 정한다. 휴대폰 GPS가 기본이고, GPS를 못 쓰는 경우에 슬라이더로 직접 입력한다.
 * 화면에는 항상 속도 요약과 "GPS로 내 속도 측정" 버튼이 보인다. 슬라이더는 "직접 입력"을 눌러 펼치고,
 * GPS를 켰는데 속도를 못 받으면(권한 거부, 사용 불가, 속도 없음) 한 번 자동으로 펼쳐지고, 그 뒤에는 언제든 접을 수 있다.
 * 위치 갱신이 GPS_STALE_MS 동안 끊기면 "직접 입력하시겠습니까?"를 물어보고, 사용자가 고르게 한다.
 * 사용처: App이 영상 아래에 둔다. 실제로 쓰이는 속도가 바뀔 때마다 onChange로 알려 서버(set_speed)에 보낸다.
 * 주의: GPS 값이 없으면 슬라이더 값을 쓴다. 슬라이더를 접어 두어도 속도 전송과 GPS 구독은 계속된다.
 *       슬라이더 값은 이 컴포넌트가 들고 있다.
 */
export function SpeedInput({ onChange }: { onChange: (speedKmh: number) => void }) {
  // 슬라이더 위치. 처음엔 서버 기본 속도와 같게 시작한다
  const [sliderKmh, setSliderKmh] = useState(DEFAULT_SPEED_KMH)
  // GPS 사용 여부 (사용자가 버튼으로 켠다)
  const [gpsOn, setGpsOn] = useState(false)
  // 슬라이더를 펼쳤는지. 처음엔 접어 두고, 버튼으로 열고 닫는다 (GPS 실패 때는 아래에서 한 번 자동으로 연다)
  const [sliderOpen, setSliderOpen] = useState(false)
  // GPS 실패로 이미 한 번 자동으로 열었는지. 사용자가 접어도 실패가 이어지는 동안 다시 열지 않기 위한 표시
  const [autoOpened, setAutoOpened] = useState(false)
  // "계속 기다리기"를 골랐는지. 신호가 돌아오면(stale이 풀리면) 다시 묻도록 아래에서 되돌린다
  const [waitChosen, setWaitChosen] = useState(false)
  const gps = useGpsSpeed(gpsOn)
  if (waitChosen && gps.status !== 'stale') setWaitChosen(false)

  // GPS를 켰고 속도 값이 있으면 그 값, 아니면 슬라이더 값. 서버에는 정수로 보내 전송량을 줄인다
  const usingGps = gpsOn && gps.speedKmh !== null
  const speedKmh = usingGps ? Math.round(gps.speedKmh ?? 0) : sliderKmh

  // GPS 실패를 확정할 수 있을 때 슬라이더를 한 번 자동으로 펼친다. 신호 대기 중과 끊김(stale)은 제외:
  // 끊김은 아래 질문으로 사용자가 정한다. 실패가 풀리면 다음 실패를 위해 표시를 되돌린다
  const gpsFailed = gpsOn && !usingGps && gps.status !== 'waiting' && gps.status !== 'stale'
  if (gpsFailed && !autoOpened) {
    setAutoOpened(true)
    setSliderOpen(true)
  } else if (!gpsFailed && autoOpened) {
    setAutoOpened(false)
  }
  // 위치 갱신이 끊겼고 아직 답하지 않았으면 직접 입력할지 묻는다
  const askManual = gpsOn && gps.status === 'stale' && !sliderOpen && !waitChosen

  // 실제로 쓰이는 속도가 바뀔 때마다 서버에 알린다 (슬라이더·GPS·전환 모두 여기 하나로 처리)
  useEffect(() => {
    onChange(speedKmh)
  }, [speedKmh, onChange])

  return (
    <div className="speed-input">
      {/* 요약 줄: 속도 출처와 현재 속도 */}
      <div className="speed-input-head">
        <span className="speed-input-title">내 속도</span>
        <output>
          {speedKmh}
          <small>km/h</small>
        </output>
      </div>
      {/* GPS 버튼은 접히지 않는 자리에 항상 둔다: 실제 주행에서는 GPS가 기본이다 */}
      <button type="button" className="speed-input-gps" aria-pressed={gpsOn} onClick={() => setGpsOn(!gpsOn)}>
        GPS로 내 속도 측정
      </button>
      {/* 위치 갱신이 끊기면 직접 입력할지 묻는다. 그동안에도 슬라이더 값이 대신 쓰인다 */}
      {askManual && (
        <div className="speed-input-prompt" role="alert">
          <p>{GPS_STALE_MS / 1000}초 동안 위치 갱신이 안 됐어요. 직접 입력하시겠습니까?</p>
          <div>
            <button type="button" onClick={() => setSliderOpen(true)}>
              직접 입력
            </button>
            <button type="button" onClick={() => setWaitChosen(true)}>
              계속 기다리기
            </button>
          </div>
        </div>
      )}
      {/* GPS를 켰는데 값이 없는 이유를 알려 준다 (질문이 떠 있는 동안은 질문으로 대신한다) */}
      {gpsOn && !usingGps && !askManual && <p className="speed-input-note">{GPS_NOTES[gps.status]}</p>}
      {/* 슬라이더는 GPS를 못 쓸 때의 대체 수단이라 GPS 버튼보다 작게 둔다. 열린 뒤에도 항상 접을 수 있다 */}
      <button
        type="button"
        className="speed-input-manual-toggle"
        aria-expanded={sliderOpen}
        onClick={() => setSliderOpen(!sliderOpen)}
      >
        직접 입력 {sliderOpen ? '▴ 접기' : '▾ 펼치기'}
      </button>
      {sliderOpen && (
        <input
          type="range"
          aria-label="내 속도 슬라이더"
          min={SPEED_MIN_KMH}
          max={SPEED_MAX_KMH}
          step={SPEED_STEP_KMH}
          value={sliderKmh}
          // GPS 값을 쓰는 동안에는 슬라이더를 잠가 두 값이 헷갈리지 않게 한다
          disabled={usingGps}
          onChange={(e) => setSliderKmh(Number(e.target.value))}
        />
      )}
    </div>
  )
}
