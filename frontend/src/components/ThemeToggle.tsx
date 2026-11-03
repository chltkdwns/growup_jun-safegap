import type { ThemeMode } from '../hooks/useTheme'

const OPTIONS: { mode: ThemeMode; label: string }[] = [
  { mode: 'system', label: '시스템' },
  { mode: 'light', label: '라이트' },
  { mode: 'dark', label: '다크' },
]

/**
 * 화면 테마(시스템 / 라이트 / 다크)를 고르는 버튼 묶음.
 * 사용처: App이 useTheme의 mode와 changeMode를 넘겨 쓴다.
 */
export function ThemeToggle({ mode, onChange }: { mode: ThemeMode; onChange: (mode: ThemeMode) => void }) {
  return (
    <div className="toggle-group" role="group" aria-label="화면 테마">
      {OPTIONS.map((option) => (
        <button key={option.mode} type="button" aria-pressed={mode === option.mode} onClick={() => onChange(option.mode)}>
          {option.label}
        </button>
      ))}
    </div>
  )
}
