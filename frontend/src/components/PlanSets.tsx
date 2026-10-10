import { useState } from 'react'
import { useExerciseHistory } from '../api/exerciseTemplates'
import { useAppSettings } from '../context/SettingsContext'
import { setSummary } from '../lib/format'
import type { TemplateExercise } from '../types'
import type { WorkoutSet } from '../types'

type Kind = 'warmup' | 'working' | 'drop'

/**
 * A template exercise's set plan: how many warm-up, working and drop sets a workout starts with.
 * Weights and reps aren't part of the plan. Each planned set shows what it will be filled with:
 * the same kind of set from the last time the exercise was done.
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

  const fillFor = (kind: Kind, index: number): string => {
    const copies = byKind[kind]
    const source = copies[index] ?? (kind === 'working' ? copies[copies.length - 1] : undefined)
    return source ? setSummary(source, settings.weight_unit) : '—'
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
      <label className="flex items-center gap-2 text-sm">
        <span className="text-muted">Rep range</span>
        <RepRangeInput value={exercise.target_reps ?? ''} onCommit={(v) => onChange({ target_reps: v || null })} />
      </label>
      <div className="space-y-0.5">
        {planned.map((row, i) => (
          <div key={i} className="flex items-center gap-3 rounded-lg py-1 text-sm">
            <span className="w-5 text-muted">{i + 1}</span>
            <span
              className={`w-6 text-[10px] font-semibold uppercase ${
                row.kind === 'warmup' ? 'text-amber-500' : row.kind === 'drop' ? 'text-accent' : 'text-transparent'
              }`}
            >
              {row.kind === 'warmup' ? 'W' : row.kind === 'drop' ? 'D' : '·'}
            </span>
            {/* Ghost text, like an empty input's placeholder: the last session's values, not set values. */}
            <span className="inline-flex h-8 min-w-[9rem] items-center rounded-md border border-dashed border-border px-2 text-sm tabular-nums text-muted/60">
              {fillFor(row.kind, row.index)}
            </span>
          </div>
        ))}
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
