import { useCallback, useEffect, useRef, useState } from 'react'

const STORAGE_PREFIX = 'workoutapp.restTimer.'

function storageKey(workoutId: number) {
  return `${STORAGE_PREFIX}${workoutId}`
}

interface StoredTimer {
  endAt: number
  durationSeconds: number
}

function readTimer(workoutId: number): StoredTimer | null {
  try {
    const raw = localStorage.getItem(storageKey(workoutId))
    if (!raw) return null
    const parsed = JSON.parse(raw) as StoredTimer
    return Number.isFinite(parsed.endAt) ? parsed : null
  } catch {
    return null
  }
}

function writeTimer(workoutId: number, timer: StoredTimer | null) {
  try {
    if (timer === null) {
      localStorage.removeItem(storageKey(workoutId))
    } else {
      localStorage.setItem(storageKey(workoutId), JSON.stringify(timer))
    }
  } catch {
    // localStorage unavailable (private mode, etc.) - timer still works in-memory for this tab
  }
}

function playChime() {
  try {
    const AudioContextClass = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    const ctx = new AudioContextClass()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.frequency.value = 880
    gain.gain.setValueAtTime(0.2, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6)
    osc.start()
    osc.stop(ctx.currentTime + 0.6)
  } catch {
    // Audio not available; silent no-op
  }
}

function notify() {
  try {
    if (Notification.permission === 'granted') {
      new Notification('Rest timer done', { body: 'Time for your next set.' })
    }
  } catch {
    // Notifications not available/permitted
  }
}

export interface RestTimerState {
  /** Seconds remaining; negative once the timer has expired (counting up). */
  secondsRemaining: number | null
  durationSeconds: number | null
  isRunning: boolean
  isExpired: boolean
  start: (durationSeconds: number) => void
  adjust: (deltaSeconds: number) => void
  clear: () => void
}

export function useRestTimer(workoutId: number | null): RestTimerState {
  const [timer, setTimer] = useState<StoredTimer | null>(() => (workoutId ? readTimer(workoutId) : null))
  const [now, setNow] = useState(() => Date.now())
  const firedRef = useRef(false)

  useEffect(() => {
    setTimer(workoutId ? readTimer(workoutId) : null)
    firedRef.current = false
  }, [workoutId])

  useEffect(() => {
    if (timer === null) return
    const interval = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(interval)
  }, [timer])

  useEffect(() => {
    if (timer === null) return
    const remaining = Math.ceil((timer.endAt - now) / 1000)
    if (remaining <= 0 && !firedRef.current) {
      firedRef.current = true
      playChime()
      notify()
    }
  }, [timer, now])

  const start = useCallback(
    (durationSeconds: number) => {
      if (workoutId === null) return
      const next: StoredTimer = { endAt: Date.now() + durationSeconds * 1000, durationSeconds }
      firedRef.current = false
      writeTimer(workoutId, next)
      setTimer(next)
      setNow(Date.now())
      if (typeof Notification !== 'undefined' && Notification.permission === 'default') {
        Notification.requestPermission().catch(() => {})
      }
    },
    [workoutId],
  )

  const adjust = useCallback(
    (deltaSeconds: number) => {
      if (workoutId === null || timer === null) return
      const next: StoredTimer = { ...timer, endAt: timer.endAt + deltaSeconds * 1000 }
      writeTimer(workoutId, next)
      setTimer(next)
    },
    [workoutId, timer],
  )

  const clear = useCallback(() => {
    if (workoutId === null) return
    writeTimer(workoutId, null)
    setTimer(null)
  }, [workoutId])

  const secondsRemaining = timer === null ? null : Math.ceil((timer.endAt - now) / 1000)

  return {
    secondsRemaining,
    durationSeconds: timer?.durationSeconds ?? null,
    isRunning: timer !== null,
    isExpired: secondsRemaining !== null && secondsRemaining <= 0,
    start,
    adjust,
    clear,
  }
}
