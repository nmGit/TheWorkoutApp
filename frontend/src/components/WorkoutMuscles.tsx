import { useMemo } from 'react'
import { useWorkoutStrength } from '../api/workouts'
import type { MuscleSummary, WorkoutStrength } from '../types'
import { COLORS, SATURATION, strengthFills, templateFills } from '../lib/strengthColors'
import { MuscleMapPair } from './MuscleMap'

/** A small front-and-back map for a completed workout card, coloured by its strength. */
export function StrengthMapThumb({ strength }: { strength?: WorkoutStrength }) {
  const fills = useMemo(() => strengthFills(strength), [strength])
  return <MuscleMapPair primary={[]} secondary={[]} fills={fills} interactive={false} className="h-24 w-24 shrink-0" />
}

/** A small front-and-back map for a template card. With a completed instance it uses that
 * instance's strength colours; with none, the muscles it will work are pure blue. */
export function TemplateMapThumb({ muscles, latest }: { muscles: MuscleSummary; latest?: WorkoutStrength }) {
  const fills = useMemo(() => (latest ? strengthFills(latest) : templateFills(muscles)), [latest, muscles])
  return <MuscleMapPair primary={[]} secondary={[]} fills={fills} interactive={false} className="h-24 w-24 shrink-0" />
}

/** The muscle groups a workout covers, its strength against your usual, and a body map
 * coloured by strength, for the top of a workout view. */
export function WorkoutMusclesHeader({ workoutId, muscles }: { workoutId: number; muscles: MuscleSummary }) {
  const { data: strength } = useWorkoutStrength(workoutId)
  const fills = useMemo(() => strengthFills(strength), [strength])
  const hasMuscles = muscles.primary.length > 0 || muscles.secondary.length > 0
  if (!hasMuscles) return null

  return (
    <div className="space-y-2">
      {muscles.groups.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {muscles.groups.map((group) => (
            <span key={group} className="rounded-full bg-accent/15 px-2.5 py-0.5 text-xs font-medium text-accent">
              {group}
            </span>
          ))}
        </div>
      )}
      <StrengthSummaryLine
        score={strength?.score ?? null}
        scoredMuscles={Object.values(strength?.muscles ?? {}).filter((m) => m.status === 'scored').length}
      />
      <StrengthLegend />
      <MuscleMapPair
        primary={[]}
        secondary={[]}
        fills={fills}
        showLabels
        interactive={false}
        className="h-56 w-full"
      />
    </div>
  )
}

function StrengthSummaryLine({ score, scoredMuscles }: { score: number | null; scoredMuscles: number }) {
  if (score === null) {
    return <p className="text-xs text-muted">Strength: building your baseline (needs a few workouts).</p>
  }
  const percent = Math.round((score - 1) * 1000) / 10
  if (percent === 0) {
    return <p className="text-sm text-muted">No change from your usual strength.</p>
  }
  const word = percent > 0 ? 'stronger' : 'weaker'
  const sign = percent > 0 ? '+' : ''
  return (
    <p className="text-sm">
      <span className={`font-semibold ${percent > 0 ? 'text-success' : 'text-danger'}`}>
        {sign}
        {percent}%
      </span>{' '}
      <span className="text-muted">
        {word} than your usual, across {scoredMuscles} {scoredMuscles === 1 ? 'muscle' : 'muscles'} with enough history
      </span>
    </p>
  )
}

function StrengthLegend() {
  const edge = `${Math.round(SATURATION * 100)}%`
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
      <span className="flex items-center gap-1.5">
        <span className="font-medium">−{edge}</span>
        <span
          className="h-2 w-16 rounded-full"
          style={{
            background: `linear-gradient(to right, rgb(${COLORS.regressed.join(', ')}), rgb(${COLORS.neutral.join(', ')}), rgb(${COLORS.improved.join(', ')}))`,
          }}
        />
        <span className="font-medium">+{edge}</span>
      </span>
      <span className="flex items-center gap-1">
        <span className="h-2.5 w-2.5 rounded-sm" style={{ background: COLORS.pending }} />
        Not done yet
      </span>
      <span className="flex items-center gap-1">
        <span className="h-2.5 w-2.5 rounded-sm" style={{ background: COLORS.noData }} />
        No data
      </span>
    </div>
  )
}
