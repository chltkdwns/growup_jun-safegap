import { useCallback, useEffect, useRef, useState } from 'react'
import { LEVEL_ORDER } from '../constants'
import type { Level } from '../constants'

interface AlarmPattern {
  freqHz: number // 소리 높이
  wave: OscillatorType // 소리 모양
  count: number // 삐 소리 횟수
  gapS: number // 삐 소리 시작 사이 간격(초)
  durS: number // 삐 소리 하나의 길이(초)
  volume: number // 소리 크기 (0~1)
}

// 단계가 높을수록 높고 빠르고 많이 울린다. 안전(safe)은 소리가 없다.
const ALARMS: Partial<Record<Level, AlarmPattern>> = {
  주의: { freqHz: 660, wave: 'sine', count: 1, gapS: 0, durS: 0.25, volume: 0.12 },
  경고: { freqHz: 880, wave: 'triangle', count: 2, gapS: 0.22, durS: 0.16, volume: 0.18 },
  위험: { freqHz: 1320, wave: 'square', count: 6, gapS: 0.12, durS: 0.08, volume: 0.2 },
}

// 삐 소리 하나를 예약한다. 소리가 딱 끊기며 "툭" 하는 잡음이 나지 않게 크기를 서서히 올렸다 내린다.
function beep(audio: AudioContext, pattern: AlarmPattern, startAt: number) {
  const osc = audio.createOscillator()
  const gain = audio.createGain()
  osc.type = pattern.wave
  osc.frequency.value = pattern.freqHz
  gain.gain.setValueAtTime(0, startAt)
  gain.gain.linearRampToValueAtTime(pattern.volume, startAt + 0.01)
  gain.gain.exponentialRampToValueAtTime(0.0001, startAt + pattern.durS)
  osc.connect(gain).connect(audio.destination)
  osc.start(startAt)
  osc.stop(startAt + pattern.durS + 0.02)
}

/**
 * 경고 단계가 올라갈 때만 경고음을 낸다 (내려가거나 그대로면 조용).
 * 사용처: App이 frame.level을 넘겨 호출하고, 켜기/끄기 버튼(SoundToggle)에 soundOn과 toggleSound를 준다.
 * 주의: 브라우저는 사용자가 한 번 누르기 전에는 소리를 막는다. 그래서 처음엔 꺼져 있고, 버튼을 눌러 켠다.
 */
export function useAlarmSound(level: Level | undefined) {
  const [soundOn, setSoundOn] = useState(false)
  const audioRef = useRef<AudioContext | null>(null)
  // 직전 프레임의 단계 순서. 지금 단계와 비교해 올랐는지 본다
  const prevIndexRef = useRef(0)

  useEffect(() => {
    if (!level) return
    // 1단계: 단계가 올랐는지 확인하고, 다음 비교를 위해 기록
    const index = LEVEL_ORDER.indexOf(level)
    const risen = index > prevIndexRef.current
    prevIndexRef.current = index

    // 2단계: 올랐고 소리가 켜져 있으면 그 단계의 소리를 낸다
    const audio = audioRef.current
    const pattern = ALARMS[level]
    if (!risen || !soundOn || !audio || !pattern) return
    for (let i = 0; i < pattern.count; i++) {
      beep(audio, pattern, audio.currentTime + i * pattern.gapS)
    }
  }, [level, soundOn])

  const toggleSound = useCallback(() => {
    // 처음 켤 때 사용자 클릭 안에서 오디오를 만들어야 브라우저가 허용한다
    if (!audioRef.current) audioRef.current = new AudioContext()
    void audioRef.current.resume()
    setSoundOn((on) => !on)
  }, [])

  return { soundOn, toggleSound }
}
