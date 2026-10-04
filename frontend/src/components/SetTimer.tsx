import { useEffect, useRef, useState } from 'react'
import { formatDuration } from '../lib/format'
import { playBing } from '../lib/bing'

interface Props {
  /** The set's planned duration in seconds, or null if none is entered. */
  target: number | null
  /** Called with the elapsed seconds when the lifter stops the timer. */
  onStop: (elapsedSeconds: number) => void
  /** Called to close the timer without saving anything. */
  onDiscard: () => void
}

const TICK_MS = 200

/** Counts up from when it mounts. At the target it bings once, then keeps counting until stopped. */
export function SetTimer({ target, onStop, onDiscard }: Props) {
  const startedAt = useRef(Date.now())
  const fired = useRef(false)
  const [elapsedMs, setElapsedMs] = useState(0)

  useEffect(() => {
    const id = window.setInterval(() => {
      const ms = Date.now() - startedAt.current
      setElapsedMs(ms)
      if (target !== null && !fired.current && ms >= target * 1000) {
        fired.current = true
        playBing()
      }
    }, TICK_MS)
    return () => window.clearInterval(id)
  }, [target])

  const elapsed = Math.round(elapsedMs / 1000)
  // The bar runs to 125% of the target, so the tick sits at 80% and there's room to keep going.
  // Past that, the bar follows the elapsed time.
  const scale = Math.max(target ? target * 1.25 : 0, elapsed, 1)
  const fill = Math.min(100, (elapsedMs / 1000 / scale) * 100)
  const tickAt = target ? (target / scale) * 100 : null
  const overTarget = target !== null && elapsed >= target

  return (
    <div className="w-full space-y-2 rounded-lg border border-border bg-bg px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <p className={`text-2xl font-semibold tabular-nums ${overTarget ? 'text-success' : 'text-fg'}`}>
          {formatDuration(elapsed)}
        </p>
        <p className="text-xs text-muted">
          {target !== null ? `Target ${formatDuration(target)}` : 'No target: enter a duration to get a tick'}
        </p>
      </div>

      <div className="relative h-2.5 w-full overflow-visible rounded-full bg-border">
        <div
          className={`h-full rounded-full ${overTarget ? 'bg-success' : 'bg-accent'}`}
          style={{ width: `${fill}%` }}
        />
        {tickAt !== null && (
          <div
            className="absolute -top-1 h-4 w-0.5 -translate-x-1/2 rounded-full bg-fg"
            style={{ left: `${tickAt}%` }}
            title="Target"
          />
        )}
      </div>

      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={onDiscard}
          className="h-9 rounded-full border border-border px-3 text-sm font-medium text-muted hover:bg-border/40"
          title="Close the timer without saving"
        >
          Discard
        </button>
        <button
          type="button"
          onClick={() => onStop(elapsed)}
          className="flex h-9 items-center gap-1.5 rounded-full bg-fg px-3 text-sm font-medium text-bg hover:opacity-90"
          title="Stop the timer and save the time to this set"
        >
          <span aria-hidden="true">■</span> Stop
        </button>
      </div>
    </div>
  )
}
