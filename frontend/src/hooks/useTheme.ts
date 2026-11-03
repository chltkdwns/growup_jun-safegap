import { useEffect, useState } from 'react'

// 시스템: 기기 설정을 따른다 / 라이트·다크: 사용자가 직접 고른 값
export type ThemeMode = 'system' | 'light' | 'dark'

const STORAGE_KEY = 'safegap-theme'

// 저장된 선택을 읽는다. 저장소를 못 쓰거나(시크릿 모드 등) 값이 이상하면 시스템으로 시작한다.
function readStoredMode(): ThemeMode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === 'light' || stored === 'dark' ? stored : 'system'
  } catch {
    return 'system'
  }
}

/**
 * 라이트/다크 선택을 관리하고 <html data-theme>에 반영한다.
 * 사용처: App이 호출해 ThemeToggle에 mode와 changeMode를 준다.
 * 시스템 모드에서는 기기의 다크 모드 설정이 바뀌면 바로 따라간다.
 */
export function useTheme() {
  const [mode, setMode] = useState<ThemeMode>(readStoredMode)

  useEffect(() => {
    // 1단계: 시스템 모드일 때 기기가 다크인지 알려 주는 감시자
    const media = window.matchMedia('(prefers-color-scheme: dark)')

    // 2단계: 실제로 쓸 테마(light/dark)를 정해 <html>에 붙인다
    const apply = () => {
      const resolved = mode === 'system' ? (media.matches ? 'dark' : 'light') : mode
      document.documentElement.dataset.theme = resolved
    }
    apply()

    // 3단계: 기기 설정이 바뀌면 다시 적용한다
    media.addEventListener('change', apply)
    return () => media.removeEventListener('change', apply)
  }, [mode])

  // 선택을 저장하고 바꾼다. 저장이 막혀 있어도 이번 방문에는 적용된다.
  const changeMode = (next: ThemeMode) => {
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // 저장 실패는 무시한다
    }
    setMode(next)
  }

  return { mode, changeMode }
}
