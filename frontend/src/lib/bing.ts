/**
 * A short "bing" for timers. Browsers only allow sound after a user gesture, so
 * primeBing() must run inside a tap or click handler. playBing() can then run later.
 */
let context: AudioContext | null = null

export function primeBing(): void {
  try {
    context ??= new AudioContext()
    if (context.state === 'suspended') void context.resume()
  } catch {
    // No audio support: the timer still works, just silently.
  }
}

export function playBing(): void {
  if (!context) return
  const now = context.currentTime
  const oscillator = context.createOscillator()
  const gain = context.createGain()
  oscillator.type = 'sine'
  oscillator.frequency.value = 880
  gain.gain.setValueAtTime(0.3, now)
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.8)
  oscillator.connect(gain).connect(context.destination)
  oscillator.start(now)
  oscillator.stop(now + 0.8)
  navigator.vibrate?.(200)
}
