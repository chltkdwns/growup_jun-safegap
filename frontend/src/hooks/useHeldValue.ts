import { useEffect, useRef, useState } from 'react'

/**
 * 값이 바뀌어도 최소 holdMs 동안은 이전 값을 그대로 보여 준다.
 * 사용처: EventBanner가 상황 문구를 최소 2초 유지할 때 쓴다 (프레임마다 값이 깜빡이는 걸 막는다).
 * 유지 시간 안에 값이 여러 번 바뀌면 시간이 지난 뒤 가장 최근 값으로 한 번만 바뀐다.
 */
export function useHeldValue<T>(value: T, holdMs: number): T {
  const [held, setHeld] = useState(value)
  // 마지막으로 보여 주는 값이 바뀐 시각. 처음엔 0이라 첫 변경은 바로 반영된다
  const changedAtRef = useRef(0)

  useEffect(() => {
    // 이미 같은 값을 보여 주고 있으면 할 일이 없다
    if (value === held) return

    // 마지막 변경 후 holdMs가 아직 안 지났으면 남은 시간만큼 기다렸다가 바꾼다
    const waitMs = Math.max(0, changedAtRef.current + holdMs - Date.now())
    const timer = setTimeout(() => {
      changedAtRef.current = Date.now()
      setHeld(value)
    }, waitMs)

    // 대기 중에 값이 또 바뀌면 이전 예약을 취소하고 최신 값으로 다시 예약한다
    return () => clearTimeout(timer)
  }, [value, held, holdMs])

  return held
}
