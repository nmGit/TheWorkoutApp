import { useEffect, useRef, useState } from 'react'
import type { TrackingType, WeightUnit, WorkoutSet } from '../types'
import { convertWeight } from '../lib/units'
import { tone, tonePlaceholderClass } from '../lib/progressionTone'
import { DurationInput } from './DurationInput'
import { SetTimer } from './SetTimer'
import { primeBing } from '../lib/bing'

/** Within this many seconds of the planned duration, a stopped timer keeps the planned value. */
const PLANNED_TOLERANCE_SECONDS = 5

function StopwatchIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <circle cx="12" cy="13" r="8" />
      <path d="M12 9v4l2.5 2.5M9.5 2.5h5M12 2.5V5" />
    </svg>
  )
}

interface Props {
  set: WorkoutSet
  index: number
  trackingType: TrackingType
  weightUnit: WeightUnit
  previousSet?: WorkoutSet
  /** The previous session's top working set -- see lib/progressionTone.ts. Used instead of
   * previousSet for tone comparisons on a progressed set, since every working set in a
   * progressed run shares the same planned value and must compare against the same "last
   * time," not whichever previous set happens to share its position. */
  progressionBaseline?: WorkoutSet
  /** What the rest field shows as ghost text while this set has no rest of its own. */
  restGhostSeconds?: number | null
  onChange: (patch: Partial<WorkoutSet>) => void
  /** `pending` carries any typed-but-not-yet-blurred field (see uncommittedPatch below) --
   * the caller merges it into the same request that marks the set complete, rather than
   * relying on blur to commit it first in a separate, potentially racing request. */
  onToggleComplete: (pending?: Partial<WorkoutSet>) => void
  onDelete: () => void
}

function displayWeight(set: WorkoutSet, weightUnit: WeightUnit): string {
  if (set.weight === null) return ''
  const converted = convertWeight(set.weight, set.weight_unit, weightUnit)
  return (Math.round(converted * 100) / 100).toString()
}

/** The planned weight in the display unit, as ghost text. */
function plannedWeight(set: WorkoutSet, weightUnit: WeightUnit): string {
  if (set.planned_weight === null) return ''
  const converted = convertWeight(set.planned_weight, set.planned_weight_unit, weightUnit)
  return (Math.round(converted * 100) / 100).toString()
}

export function SetRow({ set, index, trackingType, weightUnit, previousSet, progressionBaseline, restGhostSeconds = null, onChange, onToggleComplete, onDelete }: Props) {
  const [weight, setWeight] = useState(() => displayWeight(set, weightUnit))
  const [reps, setReps] = useState(set.reps?.toString() ?? '')
  const [duration, setDuration] = useState(set.duration_seconds?.toString() ?? '')
  // Planned values show as ghost text (placeholders), so an empty field stays empty until typed in.
  const plannedWeightText = plannedWeight(set, weightUnit) || (previousSet && displayWeight(previousSet, weightUnit)) || '-'
  const plannedRepsText = set.planned_reps?.toString() ?? (previousSet?.reps != null ? previousSet.reps.toString() : 'reps')
  // Ghost text is tinted when progressive overload actually moved this field from last time's
  // value -- a plain copy (no progression, or a warm-up/drop) has nothing to compare
  // differently, so it stays neutral. Whenever progression is active (whether or not it
  // actually changed anything -- see planned_progression_active), every working set this
  // session shares the same planned value, so all of them compare against the same
  // progressionBaseline reference; everything else compares against previousSet (this same
  // position, last time).
  const toneReference = set.planned_progression_active ? progressionBaseline : previousSet
  const previousWeightNum =
    toneReference?.weight != null ? Math.round(convertWeight(toneReference.weight, toneReference.weight_unit, weightUnit) * 100) / 100 : null
  const plannedWeightNum =
    set.planned_weight !== null ? Math.round(convertWeight(set.planned_weight, set.planned_weight_unit, weightUnit) * 100) / 100 : null
  const weightTone = tone(plannedWeightNum, previousWeightNum)
  const repsTone = tone(set.planned_reps, toneReference?.reps ?? null)
  const plannedDurationText =
    set.planned_duration_seconds?.toString() ?? (previousSet?.duration_seconds != null ? previousSet.duration_seconds.toString() : 'sec')
  const [menuOpen, setMenuOpen] = useState(false)
  const [timerOpen, setTimerOpen] = useState(false)
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
  // Same resync for reps/duration -- without it, completing a set with those fields left blank
  // (so the real value comes from its planned/previous fallback, not from typing) would leave
  // the input's local state empty even once the server fills the real value in. The field would
  // then look blank again, with its ghost text now wrong too (planned_* is cleared on completion,
  // so the placeholder falls back to the *previous session's* value at this same position, which
  // can easily differ from what was just saved).
  useEffect(() => setReps(set.reps?.toString() ?? ''), [set.reps])
  useEffect(() => setDuration(set.duration_seconds?.toString() ?? ''), [set.duration_seconds])

  // What each field would send if committed right now, or {} if it still matches the set --
  // used both by onBlur (committed on its own) and by the complete button (merged into one
  // request alongside completed: true, see uncommittedPatch below).
  const pendingWeightPatch = (): Partial<WorkoutSet> => {
    const parsed = weight === '' ? null : Number(weight)
    if (weight === displayWeight(set, weightUnit)) return {}
    // Whatever the lifter types is in the unit they're currently viewing --
    // that becomes this set's unit of record if it differs from before.
    return { weight: parsed, weight_unit: parsed !== null ? weightUnit : null }
  }
  const pendingRepsPatch = (): Partial<WorkoutSet> => {
    const parsed = reps === '' ? null : Math.round(Number(reps))
    return parsed !== set.reps ? { reps: parsed } : {}
  }
  const pendingDurationPatch = (): Partial<WorkoutSet> => {
    const parsed = duration === '' ? null : Math.round(Number(duration))
    return parsed !== set.duration_seconds ? { duration_seconds: parsed } : {}
  }
  // Every field with typed-but-not-yet-blurred text, as one patch. Completing a set while
  // still focused in a field (never having blurred it) used to lose that text: blur's own
  // commit and the complete button's click fire as two separate, concurrently in-flight
  // requests, and whichever one the server/network happened to settle last would win --
  // usually the complete request, since it carries no weight/reps at all and so looked like
  // "leave it as it was." Folding the same pending values into the complete request itself
  // means there's only one source of truth for what this click saves, not a race between two.
  const uncommittedPatch = (): Partial<WorkoutSet> => ({
    ...pendingWeightPatch(),
    ...pendingRepsPatch(),
    ...pendingDurationPatch(),
  })
  const commitIfChanged = (patch: Partial<WorkoutSet>) => {
    if (Object.keys(patch).length) onChange(patch)
  }
  const commitWeight = () => commitIfChanged(pendingWeightPatch())
  const commitReps = () => commitIfChanged(pendingRepsPatch())
  const commitDuration = () => commitIfChanged(pendingDurationPatch())

  const showWeight = trackingType === 'weight_reps' || trackingType === 'bodyweight_reps'
  const showReps = trackingType === 'weight_reps' || trackingType === 'bodyweight_reps'
  const showDuration = trackingType === 'time' || trackingType === 'cardio'
  const showTimer = trackingType === 'time'
  // The planned duration is the duration field's value, or its ghost value (the previous
  // set's duration) when the field is empty.
  const enteredSeconds = duration.trim() === '' || Number.isNaN(Number(duration)) ? null : Math.round(Number(duration))
  const plannedSeconds = enteredSeconds ?? set.planned_duration_seconds ?? previousSet?.duration_seconds ?? null

  const finishTimer = (elapsedSeconds: number) => {
    const withinPlan =
      plannedSeconds !== null && Math.abs(elapsedSeconds - plannedSeconds) <= PLANNED_TOLERANCE_SECONDS
    const value = withinPlan ? plannedSeconds : elapsedSeconds
    setDuration(value.toString())
    onChange({ duration_seconds: value })
    // Completing a set starts its rest timer, so only do it when the set isn't already done.
    if (!set.completed) onToggleComplete()
    setTimerOpen(false)
  }

  return (
    <div className={`flex flex-wrap items-center gap-x-1 gap-y-1 rounded-lg py-1.5 ${set.is_warmup ? 'opacity-70' : ''}`}>
      <div className="flex w-7 shrink-0 flex-col items-center">
        <span className="text-sm font-medium text-muted">{index + 1}</span>
        {set.is_warmup && <span className="text-[9px] font-semibold uppercase text-amber-500">W</span>}
        {set.is_dropset && <span className="text-[9px] font-semibold uppercase text-accent">D</span>}
        {set.planned_is_progressed ? (
          <span
            className="text-[9px] font-semibold uppercase text-success"
            title="This set's ghost values come from progressive overload actually raising them"
          >
            P
          </span>
        ) : (
          set.planned_progression_active && (
            <span
              className="text-[9px] font-semibold uppercase text-muted"
              title="Progressive overload is active for this exercise, but didn't change anything for this set"
            >
              P
            </span>
          )
        )}
      </div>

      {showWeight && (
        <input
          type="number"
          inputMode="decimal"
          value={weight}
          placeholder={plannedWeightText}
          onChange={(e) => setWeight(e.target.value)}
          onBlur={commitWeight}
          className={`h-10 w-[52px] rounded-md border border-border bg-bg px-1.5 text-center text-sm tabular-nums ${tonePlaceholderClass(weightTone)}`}
        />
      )}
      {showWeight && <span className="text-xs text-muted">{weightUnit}</span>}

      {showReps && (
        <input
          type="number"
          inputMode="numeric"
          value={reps}
          placeholder={plannedRepsText}
          aria-label="reps"
          onChange={(e) => setReps(e.target.value)}
          onBlur={commitReps}
          className={`h-10 w-[52px] rounded-md border border-border bg-bg px-1.5 text-center text-sm tabular-nums ${tonePlaceholderClass(repsTone)}`}
        />
      )}
      {showDuration && (
        <input
          type="number"
          inputMode="numeric"
          value={duration}
          placeholder={plannedDurationText}
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
        {showTimer && (
          <button
            type="button"
            onClick={() => {
              // Runs inside the tap, so the bing is allowed to sound later.
              primeBing()
              setTimerOpen((open) => !open)
            }}
            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border hover:bg-border/40 ${
              timerOpen ? 'bg-border/40 text-accent' : 'text-muted'
            }`}
            title="Start a timer for this set"
            aria-label="Start timer"
            aria-expanded={timerOpen}
          >
            <StopwatchIcon />
          </button>
        )}
        <button
          type="button"
          onClick={() => onToggleComplete(uncommittedPatch())}
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

      {showTimer && timerOpen && (
        <SetTimer
          target={plannedSeconds}
          onStop={finishTimer}
          onDiscard={() => setTimerOpen(false)}
        />
      )}
    </div>
  )
}
