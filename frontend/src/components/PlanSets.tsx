import { useState } from 'react'
import { useExerciseHistory, useExercisePlanPreview } from '../api/exerciseTemplates'
import { useAppSettings } from '../context/SettingsContext'
import { formatDuration, formatWeight } from '../lib/format'
import { tone, toneTextClass } from '../lib/progressionTone'
import { convertWeight } from '../lib/units'
import type { PlanPreviewSet, TemplateExercise, WeightUnit } from '../types'
import type { WorkoutSet } from '../types'

type Kind = 'warmup' | 'working' | 'drop'
type SetLike = { weight: number | null; weight_unit: WeightUnit | null; reps: number | null; duration_seconds: number | null }

/**
 * A template exercise's set plan: how many warm-up, working and drop sets a workout starts with.
 * Weights and reps aren't part of the plan. Each planned set shows what it will be filled with --
 * live progressive overload (what starting a workout right now would actually plan), falling back
 * to a plain copy of the last session while that loads or for warm-ups/drops (never progressed).
 * Tinted green/amber the same way the active workout screen's ghost text is, with a small "P"
 * badge on a set progression actually changed (see lib/progressionTone.ts).
 */
export function PlanSets({
  exercise,
  onChange,
}: {
  exercise: TemplateExercise
  onChange: (patch: Partial<Pick<TemplateExercise, 'warmup_sets' | 'target_sets' | 'drop_sets' | 'target_reps'>>) => void
}) {
  const settings = useAppSettings()
  const { data: history } = useExerciseHistory(exercise.exercise_id)
  const { data: preview } = useExercisePlanPreview(exercise.exercise_id, {
    warmupSets: exercise.warmup_sets,
    targetSets: exercise.target_sets ?? 1,
    dropSets: exercise.drop_sets,
    targetReps: exercise.target_reps,
  })
  const lastSession: WorkoutSet[] = history?.items[0]?.sets ?? []
  const byKind: Record<Kind, WorkoutSet[]> = { warmup: [], working: [], drop: [] }
  for (const s of lastSession) {
    if (!s.completed) continue
    byKind[s.is_warmup ? 'warmup' : s.is_dropset ? 'drop' : 'working'].push(s)
  }

  const kindRows = (kind: Kind, count: number) => Array.from({ length: count }, (_, index) => ({ kind, index }))
  const planned = [
    ...kindRows('warmup', exercise.warmup_sets),
    ...kindRows('working', exercise.target_sets ?? 1),
    ...kindRows('drop', exercise.drop_sets),
  ]

  const previousFor = (kind: Kind, index: number): WorkoutSet | undefined => {
    const copies = byKind[kind]
    return copies[index] ?? (kind === 'working' ? copies[copies.length - 1] : undefined)
  }

  // Weight converted to the display unit and rounded the same way it's shown, so comparing two
  // values for tone isn't thrown off by a leftover fraction from the unit conversion.
  const normalize = (entry: SetLike | undefined, weightUnit: WeightUnit) => {
    if (!entry) return { weight: null as number | null, reps: null as number | null, duration: null as number | null }
    const weight = entry.weight !== null ? Math.round(convertWeight(entry.weight, entry.weight_unit, weightUnit) * 10) / 10 : null
    return { weight, reps: entry.reps, duration: entry.duration_seconds }
  }

  const counter = (label: string, value: number, min: number, key: 'warmup_sets' | 'target_sets' | 'drop_sets') => (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-muted">{label}</span>
      <button
        type="button"
        onClick={() => onChange({ [key]: Math.max(min, value - 1) })}
        disabled={value <= min}
        className="h-8 w-8 rounded-full border border-border hover:bg-border/40 disabled:opacity-40"
        aria-label={`Fewer ${label.toLowerCase()}`}
      >
        −
      </button>
      <span className="w-5 text-center tabular-nums">{value}</span>
      <button
        type="button"
        onClick={() => onChange({ [key]: value + 1 })}
        className="h-8 w-8 rounded-full border border-border hover:bg-border/40"
        aria-label={`More ${label.toLowerCase()}`}
      >
        +
      </button>
    </div>
  )

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-x-5 gap-y-2">
        {counter('Warm-up', exercise.warmup_sets, 0, 'warmup_sets')}
        {counter('Sets', exercise.target_sets ?? 1, 1, 'target_sets')}
        {counter('Drop', exercise.drop_sets, 0, 'drop_sets')}
      </div>
      <div className="space-y-1">
        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted">Rep range</span>
          <RepRangeInput value={exercise.target_reps ?? ''} onCommit={(v) => onChange({ target_reps: v || null })} />
        </label>
        <p className="text-xs text-muted">
          Progressive overload works toward this range for this exercise, instead of the default range
          from Settings → Generated Workouts.{' '}
          <a
            href="/docs/features/progressive_overload.html"
            target="_blank"
            rel="noreferrer"
            title="Open the user manual's progressive overload section"
            className="font-medium hover:text-accent"
          >
            Learn more
          </a>
        </p>
      </div>
      <div className="space-y-0.5">
        {planned.map((row, i) => {
          const previewEntry: PlanPreviewSet | undefined = preview?.[i]
          const previousEntry = previousFor(row.kind, row.index)
          const prev = normalize(previousEntry, settings.weight_unit)
          // Show the live preview once it's in; a plain copy of last time (no color, no badge)
          // until then, so the row never flashes empty while the preview loads.
          const next = previewEntry ? normalize(previewEntry, settings.weight_unit) : prev
          const progressed = previewEntry?.is_progressed ?? false
          const repsTone = tone(next.reps, prev.reps)
          const weightTone = tone(next.weight, prev.weight)

          let content
          if (next.weight !== null && next.reps !== null) {
            content = (
              <>
                <span className={toneTextClass(repsTone)}>{next.reps}</span>
                <span className="text-muted/60"> × </span>
                <span className={toneTextClass(weightTone)}>{formatWeight(next.weight, settings.weight_unit)}</span>
              </>
            )
          } else if (next.reps !== null) {
            content = <span className={toneTextClass(repsTone)}>{next.reps} reps</span>
          } else if (next.duration !== null) {
            content = <span className="text-muted/60">{formatDuration(next.duration)}</span>
          } else {
            content = <span className="text-muted/60">—</span>
          }

          return (
            <div key={i} className="flex items-center gap-3 rounded-lg py-1 text-sm">
              <span className="w-5 text-muted">{i + 1}</span>
              <span
                className={`w-6 text-[10px] font-semibold uppercase ${
                  row.kind === 'warmup'
                    ? 'text-amber-500'
                    : row.kind === 'drop'
                      ? 'text-accent'
                      : progressed
                        ? 'text-success'
                        : 'text-transparent'
                }`}
                title={progressed ? "This set's preview comes from progressive overload" : undefined}
              >
                {row.kind === 'warmup' ? 'W' : row.kind === 'drop' ? 'D' : progressed ? 'P' : '·'}
              </span>
              {/* Ghost text, like an empty input's placeholder: what this set will be filled with,
                  not a set value entered yet. */}
              <span className="inline-flex h-8 min-w-[9rem] items-center rounded-md border border-dashed border-border px-2 text-sm tabular-nums">
                {content}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/** The rep range a workout progresses toward, like "6-8". Saved when the field loses focus. */
function RepRangeInput({ value, onCommit }: { value: string; onCommit: (v: string) => void }) {
  const [text, setText] = useState(value)
  return (
    <input
      value={text}
      placeholder="8-12"
      onChange={(e) => setText(e.target.value)}
      onBlur={() => {
        if (text.trim() !== value) onCommit(text.trim())
      }}
      className="h-8 w-20 rounded-md border border-border bg-bg px-2 text-center text-sm tabular-nums"
    />
  )
}
