import { useEffect, useRef, useState } from 'react'
import type { TrackingType, WeightUnit, WorkoutSet } from '../types'
import { convertWeight } from '../lib/units'
import { DurationInput } from './DurationInput'

interface Props {
  set: WorkoutSet
  index: number
  trackingType: TrackingType
  weightUnit: WeightUnit
  previousSet?: WorkoutSet
  /** What the rest field shows as ghost text while this set has no rest of its own. */
  restGhostSeconds?: number | null
  onChange: (patch: Partial<WorkoutSet>) => void
  onToggleComplete: () => void
  onDelete: () => void
}

function displayWeight(set: WorkoutSet, weightUnit: WeightUnit): string {
  if (set.weight === null) return ''
  const converted = convertWeight(set.weight, set.weight_unit, weightUnit)
  return (Math.round(converted * 100) / 100).toString()
}

export function SetRow({ set, index, trackingType, weightUnit, previousSet, restGhostSeconds = null, onChange, onToggleComplete, onDelete }: Props) {
  const [weight, setWeight] = useState(() => displayWeight(set, weightUnit))
  const [reps, setReps] = useState(set.reps?.toString() ?? '')
  const [duration, setDuration] = useState(set.duration_seconds?.toString() ?? '')
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Warmup/drop-set toggles and delete are rare compared to marking a set complete --
  // tucking them behind this menu keeps the always-visible button count low
  // enough to fit narrow phone widths without wrapping.
  useEffect(() => {
    if (!menuOpen) return
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent) {
        if (e.key === 'Escape') setMenuOpen(false)
        return
      }
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', close)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', close)
    }
  }, [menuOpen])

  // Resync if the set's stored value/unit or the display unit changes out
  // from under this row (e.g. the global unit setting is flipped, or a
  // server round-trip updates the value) -- this component instance stays
  // mounted across re-renders (keyed by set.id), so plain useState alone
  // would only ever reflect the value at first mount.
  useEffect(() => setWeight(displayWeight(set, weightUnit)), [set.weight, set.weight_unit, weightUnit])

  const commitWeight = () => {
    const parsed = weight === '' ? null : Number(weight)
    const currentDisplayed = displayWeight(set, weightUnit)
    if (weight === currentDisplayed) return
    // Whatever the lifter types is in the unit they're currently viewing --
    // that becomes this set's unit of record if it differs from before.
    onChange({ weight: parsed, weight_unit: parsed !== null ? weightUnit : null })
  }
  const commitReps = () => {
    const parsed = reps === '' ? null : Math.round(Number(reps))
    if (parsed !== set.reps) onChange({ reps: parsed })
  }
  const commitDuration = () => {
    const parsed = duration === '' ? null : Math.round(Number(duration))
    if (parsed !== set.duration_seconds) onChange({ duration_seconds: parsed })
  }

  const showWeight = trackingType === 'weight_reps' || trackingType === 'bodyweight_reps'
  const showReps = trackingType === 'weight_reps' || trackingType === 'bodyweight_reps'
  const showDuration = trackingType === 'time' || trackingType === 'cardio'

  return (
    <div className={`flex flex-wrap items-center gap-x-1 gap-y-1 rounded-lg py-1.5 ${set.is_warmup ? 'opacity-70' : ''}`}>
      <div className="flex w-7 shrink-0 flex-col items-center">
        <span className="text-sm font-medium text-muted">{index + 1}</span>
        {set.is_warmup && <span className="text-[9px] font-semibold uppercase text-amber-500">W</span>}
        {set.is_dropset && <span className="text-[9px] font-semibold uppercase text-accent">D</span>}
      </div>

      {showWeight && (
        <input
          type="number"
          inputMode="decimal"
          value={weight}
          placeholder={(previousSet && displayWeight(previousSet, weightUnit)) || '-'}
          onChange={(e) => setWeight(e.target.value)}
          onBlur={commitWeight}
          className="h-10 w-[52px] rounded-md border border-border bg-bg px-1.5 text-center text-sm tabular-nums placeholder:text-muted"
        />
      )}
      {showWeight && <span className="text-xs text-muted">{weightUnit}</span>}

      {showReps && (
        <input
          type="number"
          inputMode="numeric"
          value={reps}
          placeholder={previousSet?.reps != null ? previousSet.reps.toString() : 'reps'}
          aria-label="reps"
          onChange={(e) => setReps(e.target.value)}
          onBlur={commitReps}
          className="h-10 w-[52px] rounded-md border border-border bg-bg px-1.5 text-center text-sm tabular-nums placeholder:text-muted"
        />
      )}
      {showDuration && (
        <input
          type="number"
          inputMode="numeric"
          value={duration}
          placeholder={previousSet?.duration_seconds != null ? previousSet.duration_seconds.toString() : 'sec'}
          onChange={(e) => setDuration(e.target.value)}
          onBlur={commitDuration}
          className="h-10 w-20 rounded-md border border-border bg-bg px-2 text-center text-sm tabular-nums placeholder:text-muted"
        />
      )}
      {showDuration && <span className="text-xs text-muted">sec</span>}

      <DurationInput
        value={set.rest_seconds}
        placeholderSeconds={restGhostSeconds}
        onCommit={(seconds) => onChange({ rest_seconds: seconds })}
        label="Rest after this set (m:ss)"
        title="Rest after this set (m:ss, or seconds)"
        className="h-10 w-[52px] rounded-md border border-border bg-bg px-1 text-center text-sm tabular-nums placeholder:text-muted"
      />

      <div className="ml-auto flex items-center gap-1">
        <button
          type="button"
          onClick={onToggleComplete}
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 ${
            set.completed ? 'border-success bg-success text-white' : 'border-border text-muted'
          }`}
          title={set.completed ? 'Mark set incomplete' : 'Mark set complete (starts the rest timer)'}
          aria-label={set.completed ? 'Mark incomplete' : 'Mark complete'}
        >
          ✓
        </button>
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setMenuOpen((open) => !open)}
            className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-muted hover:bg-border/40 ${
              menuOpen ? 'bg-border/40' : ''
            }`}
            title="More set actions"
            aria-label="More set actions"
            aria-expanded={menuOpen}
          >
            ⋯
          </button>
          {menuOpen && (
            <div className="absolute right-0 top-full z-10 mt-1 flex w-36 flex-col overflow-hidden rounded-lg border border-border bg-surface py-1 shadow-lg">
              {/* A set is a warmup, a drop set, or neither -- never both. */}
              <button
                type="button"
                onClick={() => {
                  onChange({ is_warmup: !set.is_warmup, is_dropset: false })
                  setMenuOpen(false)
                }}
                className="px-3 py-2 text-left text-sm text-fg hover:bg-border/40"
              >
                {set.is_warmup ? 'Unmark warmup' : 'Mark as warmup'}
              </button>
              <button
                type="button"
                onClick={() => {
                  onChange({ is_dropset: !set.is_dropset, is_warmup: false })
                  setMenuOpen(false)
                }}
                title="A drop set follows the previous set at reduced weight, with no rest in between"
                className="px-3 py-2 text-left text-sm text-fg hover:bg-border/40"
              >
                {set.is_dropset ? 'Unmark drop set' : 'Mark as drop set'}
              </button>
              <button
                type="button"
                onClick={() => {
                  onDelete()
                  setMenuOpen(false)
                }}
                className="px-3 py-2 text-left text-sm text-danger hover:bg-border/40"
              >
                Delete set
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
