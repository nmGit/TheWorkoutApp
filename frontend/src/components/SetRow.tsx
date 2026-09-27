import { useEffect, useState } from 'react'
import type { TrackingType, WeightUnit, WorkoutSet } from '../types'
import { convertWeight } from '../lib/units'

interface Props {
  set: WorkoutSet
  index: number
  trackingType: TrackingType
  weightUnit: WeightUnit
  previousLabel?: string
  onChange: (patch: Partial<WorkoutSet>) => void
  onToggleComplete: () => void
  onDelete: () => void
}

function displayWeight(set: WorkoutSet, weightUnit: WeightUnit): string {
  if (set.weight === null) return ''
  const converted = convertWeight(set.weight, set.weight_unit, weightUnit)
  return (Math.round(converted * 100) / 100).toString()
}

export function SetRow({ set, index, trackingType, weightUnit, previousLabel, onChange, onToggleComplete, onDelete }: Props) {
  const [weight, setWeight] = useState(() => displayWeight(set, weightUnit))
  const [reps, setReps] = useState(set.reps?.toString() ?? '')
  const [duration, setDuration] = useState(set.duration_seconds?.toString() ?? '')

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
    <div className={`flex items-center gap-2 rounded-lg py-1.5 ${set.is_warmup ? 'opacity-70' : ''}`}>
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
          placeholder={previousLabel ?? '-'}
          onChange={(e) => setWeight(e.target.value)}
          onBlur={commitWeight}
          className="h-10 w-16 rounded-md border border-border bg-bg px-2 text-center text-sm tabular-nums"
        />
      )}
      {showWeight && <span className="text-xs text-muted">{weightUnit}</span>}

      {showReps && (
        <input
          type="number"
          inputMode="numeric"
          value={reps}
          placeholder="reps"
          onChange={(e) => setReps(e.target.value)}
          onBlur={commitReps}
          className="h-10 w-16 rounded-md border border-border bg-bg px-2 text-center text-sm tabular-nums"
        />
      )}
      {showReps && <span className="text-xs text-muted">reps</span>}

      {showDuration && (
        <input
          type="number"
          inputMode="numeric"
          value={duration}
          placeholder="sec"
          onChange={(e) => setDuration(e.target.value)}
          onBlur={commitDuration}
          className="h-10 w-20 rounded-md border border-border bg-bg px-2 text-center text-sm tabular-nums"
        />
      )}
      {showDuration && <span className="text-xs text-muted">sec</span>}

      <div className="ml-auto flex items-center gap-1">
        <button
          type="button"
          onClick={() => onChange({ is_warmup: !set.is_warmup })}
          className={`h-8 w-8 rounded-full text-[10px] font-bold uppercase ${
            set.is_warmup ? 'bg-amber-500/20 text-amber-600' : 'text-muted hover:bg-border/40'
          }`}
          title="Toggle warmup set"
          aria-label="Toggle warmup set"
        >
          W
        </button>
        <button
          type="button"
          onClick={onToggleComplete}
          className={`flex h-9 w-9 items-center justify-center rounded-full border-2 ${
            set.completed ? 'border-success bg-success text-white' : 'border-border text-muted'
          }`}
          title={set.completed ? 'Mark set incomplete' : 'Mark set complete (starts the rest timer)'}
          aria-label={set.completed ? 'Mark incomplete' : 'Mark complete'}
        >
          ✓
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="h-8 w-8 rounded-full text-muted hover:bg-border/40"
          title="Delete this set"
          aria-label="Delete set"
        >
          ✕
        </button>
      </div>
    </div>
  )
}
