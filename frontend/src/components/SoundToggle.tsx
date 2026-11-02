/**
 * 경고음 켜기/끄기 버튼.
 * 사용처: App이 useAlarmSound의 soundOn과 toggleSound를 넘겨 쓴다.
 * 브라우저가 소리를 막지 않도록 사용자가 직접 눌러야 소리가 켜진다.
 */
export function SoundToggle({ soundOn, onToggle }: { soundOn: boolean; onToggle: () => void }) {
  return (
    <button type="button" aria-pressed={soundOn} onClick={onToggle}>
      {soundOn ? '경고음 켜짐' : '경고음 꺼짐'}
    </button>
  )
}
