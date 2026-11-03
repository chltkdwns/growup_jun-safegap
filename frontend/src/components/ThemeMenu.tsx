import { useState } from 'react'
import type { ThemeMode } from '../hooks/useTheme'
import { ThemeToggle } from './ThemeToggle'
import './ThemeMenu.css'

/**
 * 오른쪽 위 햄버거 버튼. 누르면 화면 테마(시스템/라이트/다크) 선택이 펼쳐진다.
 * 사용처: App 헤더. 세로(앱) 화면에서만 보이고, 가로(웹) 화면에서는 CSS가 숨긴다(오른쪽 패널에 같은 버튼이 있다).
 */
export function ThemeMenu({ mode, onChange }: { mode: ThemeMode; onChange: (mode: ThemeMode) => void }) {
  // 메뉴를 펼쳤는지
  const [open, setOpen] = useState(false)

  return (
    <div className="theme-menu">
      <button type="button" className="theme-menu-button" aria-label="메뉴" aria-expanded={open} onClick={() => setOpen(!open)}>
        ☰
      </button>
      {open && (
        <div className="theme-menu-popover">
          <p>화면 모드</p>
          <ThemeToggle mode={mode} onChange={onChange} />
        </div>
      )}
    </div>
  )
}
