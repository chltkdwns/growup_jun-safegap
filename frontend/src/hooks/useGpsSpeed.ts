import { useEffect, useState } from 'react'
import { MS_TO_KMH } from '../constants'

// GPS 상태: 아직 모름(대기) / 값 수신 중 / 사용자가 위치 권한을 거부 / 이 기기·주소에서 사용 불가
export type GpsStatus = 'waiting' | 'ok' | 'denied' | 'unavailable'

// 브라우저가 위치 기능을 줄 때만 true. HTTPS가 아닌 주소(localhost 제외)에서는 undefined가 되기도 한다.
const GPS_SUPPORTED = typeof navigator !== 'undefined' && 'geolocation' in navigator

/**
 * 휴대폰 GPS로 내 속도(km/h)를 실시간으로 읽는다.
 * 사용처: SpeedInput이 "GPS 사용"을 켰을 때 호출한다. 값이 없으면 SpeedInput이 슬라이더 값으로 대신한다.
 * 입력: enabled 켜져 있을 때만 위치를 구독한다 (꺼지면 구독을 끊어 배터리를 아낀다)
 * 출력: speedKmh 가장 최근 속도(km/h). 정차 직후·신호 약함 등으로 속도를 모르면 null. status 현재 상태.
 * 주의: 위치 권한 허용이 필요하다. 데스크톱은 보통 속도를 주지 않아 null이다.
 */
export function useGpsSpeed(enabled: boolean) {
  const [speedKmh, setSpeedKmh] = useState<number | null>(null)
  const [status, setStatus] = useState<GpsStatus>('waiting')

  useEffect(() => {
    if (!enabled || !GPS_SUPPORTED) return

    // 위치가 갱신될 때마다 호출된다. coords.speed는 m/s이고 모르면 null이다
    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        const speedMps = position.coords.speed
        setSpeedKmh(speedMps == null ? null : speedMps * MS_TO_KMH)
        setStatus('ok')
      },
      // 권한 거부(code 1)와 그 밖의 실패(신호 없음 등)를 나눠서 알려 준다
      (error) => {
        setSpeedKmh(null)
        setStatus(error.code === error.PERMISSION_DENIED ? 'denied' : 'unavailable')
      },
      // 높은 정확도 모드: 속도 값은 이 모드에서만 믿을 만하다. 1초 안의 캐시는 허용한다
      { enableHighAccuracy: true, maximumAge: 1000 },
    )

    // 끄거나 화면을 떠날 때 구독을 끊고 값을 비운다 (다시 켰을 때 옛 값이 보이지 않게)
    return () => {
      navigator.geolocation.clearWatch(watchId)
      setSpeedKmh(null)
      setStatus('waiting')
    }
  }, [enabled])

  // 위치 기능 자체가 없으면 effect 없이 바로 사용 불가로 본다
  return { speedKmh, status: GPS_SUPPORTED ? status : ('unavailable' as GpsStatus) }
}
