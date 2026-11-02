import { useEffect, useState } from 'react'
import { DEFAULT_SPEED_KMH, SPEED_MAX_KMH, SPEED_MIN_KMH, SPEED_STEP_KMH } from '../constants'
import { useGpsSpeed } from '../hooks/useGpsSpeed'
import type { GpsStatus } from '../hooks/useGpsSpeed'
import './SpeedInput.css'

// GPS를 켰지만 값이 아직 없을 때 보여 줄 안내. 이때는 슬라이더 값이 대신 쓰인다
const GPS_NOTES: Record<GpsStatus, string> = {
  waiting: 'GPS 신호를 기다리는 중이에요. 그동안 슬라이더 값을 써요.',
  ok: 'GPS가 속도를 알려 주지 않아요. 슬라이더 값을 써요.',
  denied: '위치 권한이 꺼져 있어요. 슬라이더 값을 써요.',
  unavailable: '이 기기나 주소에서는 GPS를 쓸 수 없어요. 슬라이더 값을 써요.',
}

/**
 * 내 속도를 정한다. 기본은 슬라이더 직접 입력이고, "GPS 사용"을 켜면 휴대폰 GPS 속도를 우선 쓴다.
 * 사용처: App이 영상 아래에 둔다. 실제로 쓰이는 속도가 바뀔 때마다 onChange로 알려 서버(set_speed)에 보낸다.
 * 주의: GPS가 속도를 주지 못하면(권한 거부, 신호 없음, 데스크톱 등) 슬라이더 값으로 자동으로 돌아간다.
 *       슬라이더 값은 이 컴포넌트가 들고 있다. 서버를 다시 켜면 서버 속도는 기본값으로 돌아가지만 슬라이더는 그대로다.
 */
export function SpeedInput({ onChange }: { onChange: (speedKmh: number) => void }) {
  // 슬라이더 위치. 처음엔 서버 기본 속도와 같게 시작한다
  const [sliderKmh, setSliderKmh] = useState(DEFAULT_SPEED_KMH)
  // GPS 사용 여부 (사용자가 버튼으로 켠다)
  const [gpsOn, setGpsOn] = useState(false)
  const gps = useGpsSpeed(gpsOn)

  // GPS를 켰고 속도 값이 있으면 그 값, 아니면 슬라이더 값. 서버에는 정수로 보내 전송량을 줄인다
  const usingGps = gpsOn && gps.speedKmh !== null
  const speedKmh = usingGps ? Math.round(gps.speedKmh ?? 0) : sliderKmh

  // 실제로 쓰이는 속도가 바뀔 때마다 서버에 알린다 (슬라이더·GPS·전환 모두 여기 하나로 처리)
  useEffect(() => {
    onChange(speedKmh)
  }, [speedKmh, onChange])

  return (
    <div className="speed-input">
      <label htmlFor="speed-input-range">내 속도 · {usingGps ? 'GPS' : '직접 입력'}</label>
      <output>
        {speedKmh}
        <small>km/h</small>
      </output>
      <input
        id="speed-input-range"
        type="range"
        min={SPEED_MIN_KMH}
        max={SPEED_MAX_KMH}
        step={SPEED_STEP_KMH}
        value={sliderKmh}
        // GPS 값을 쓰는 동안에는 슬라이더를 잠가 두 값이 헷갈리지 않게 한다
        disabled={usingGps}
        onChange={(e) => setSliderKmh(Number(e.target.value))}
      />
      <button type="button" className="speed-input-gps" aria-pressed={gpsOn} onClick={() => setGpsOn(!gpsOn)}>
        GPS 사용
      </button>
      {/* GPS를 켰는데 값이 없는 이유를 알려 준다 */}
      {gpsOn && !usingGps && <p className="speed-input-note">{GPS_NOTES[gps.status]}</p>}
    </div>
  )
}
