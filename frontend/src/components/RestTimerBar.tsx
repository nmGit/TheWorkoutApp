import { useGlobalRestTimer } from '../context/RestTimerContext'
import { formatDuration } from '../lib/format'

export function RestTimerBar() {
  const timer = useGlobalRestTimer()

  if (!timer.isRunning || timer.secondsRemaining === null) return null

  const total = timer.durationSeconds ?? 1
  const progress = timer.isExpired ? 1 : Math.max(0, Math.min(1, 1 - timer.secondsRemaining / total))

  return (
    <div
      className="sticky top-0 z-40 border-b border-border bg-surface/95 px-4 py-3 shadow-[0_4px_12px_rgba(0,0,0,0.08)] backdrop-blur"
      role="status"
      aria-live="polite"
    >
      <div className="mx-auto flex max-w-xl items-center gap-4">
        <div className="relative h-12 w-12 shrink-0">
          <svg viewBox="0 0 36 36" className="h-12 w-12 -rotate-90">
            <circle cx="18" cy="18" r="15.5" fill="none" stroke="currentColor" strokeWidth="3" className="text-border" />
            <circle
              cx="18"
              cy="18"
              r="15.5"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              strokeDasharray={2 * Math.PI * 15.5}
              strokeDashoffset={2 * Math.PI * 15.5 * (1 - progress)}
              strokeLinecap="round"
              className={timer.isExpired ? 'text-muted' : 'text-accent'}
            />
          </svg>
        </div>

        <div className="flex-1">
          <p className="text-xs uppercase tracking-wide text-muted">
            {timer.isExpired ? 'Rest over' : 'Resting'}
          </p>
          <p className={`text-xl font-semibold tabular-nums ${timer.isExpired ? 'text-muted' : 'text-fg'}`}>
            {/* Past the end of the rest, the timer counts up as overtime. */}
            {timer.secondsRemaining < 0 ? `+${formatDuration(-timer.secondsRemaining)}` : formatDuration(timer.secondsRemaining)}
          </p>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => timer.adjust(-15)}
            className="h-9 min-w-9 rounded-full border border-border px-2 text-sm font-medium hover:bg-border/40"
            title="Subtract 15 seconds"
            aria-label="Subtract 15 seconds"
          >
            -15
          </button>
          <button
            type="button"
            onClick={() => timer.adjust(15)}
            className="h-9 min-w-9 rounded-full border border-border px-2 text-sm font-medium hover:bg-border/40"
            title="Add 15 seconds"
            aria-label="Add 15 seconds"
          >
            +15
          </button>
          <button
            type="button"
            onClick={() => timer.clear()}
            className="h-9 rounded-full bg-fg px-3 text-sm font-medium text-bg hover:opacity-90"
            title="Skip the rest of this timer"
          >
            Skip
          </button>
        </div>
      </div>
    </div>
  )
}
