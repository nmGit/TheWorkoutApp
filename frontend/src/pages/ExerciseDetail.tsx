import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useExercise, useExerciseHistory, useUpdateExercise } from '../api/exercises'
import { useExerciseStats } from '../api/stats'
import { ProgressChart } from '../components/ProgressChart'
import { Card, LoadingState, PageTitle } from '../components/ui'
import { useAppSettings } from '../context/SettingsContext'
import { formatDate, formatDuration, formatWeight, setSummary } from '../lib/format'

const METRIC_LABELS: Record<string, string> = {
  max_weight: 'Max weight',
  est_1rm: 'Estimated 1RM',
  volume: 'Volume',
  best_set_volume: 'Best set volume',
  distance: 'Distance',
  pace: 'Pace',
  longest_distance: 'Longest distance',
  fastest_pace: 'Fastest pace',
}

export function ExerciseDetailPage() {
  const { id } = useParams()
  const exerciseId = Number(id)
  const settings = useAppSettings()
  const { data: exercise } = useExercise(exerciseId)
  const { data: history } = useExerciseHistory(exerciseId)
  const updateExercise = useUpdateExercise(exerciseId)

  const defaultMetric = exercise?.tracking_type === 'cardio' ? 'distance' : 'est_1rm'
  const [metric, setMetric] = useState<string | undefined>(undefined)
  const activeMetric = metric ?? defaultMetric
  const { data: stats } = useExerciseStats(exerciseId, activeMetric)

  if (!exercise) return <LoadingState />

  const unit = activeMetric === 'distance' ? settings.distance_unit : settings.weight_unit
  const availableMetrics =
    exercise.tracking_type === 'cardio' ? ['distance', 'pace'] : ['est_1rm', 'max_weight', 'volume']

  return (
    <div className="space-y-4">
      <PageTitle>{exercise.name}</PageTitle>
      <p className="-mt-3 text-sm text-muted">
        {exercise.muscle_group_name} · {exercise.equipment}
      </p>

      <Card className="space-y-3">
        <div className="flex gap-1.5">
          {availableMetrics.map((m) => (
            <button
              key={m}
              onClick={() => setMetric(m)}
              title={`Chart ${METRIC_LABELS[m]?.toLowerCase() ?? m} over time`}
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                activeMetric === m ? 'bg-accent text-accent-fg' : 'bg-border/50 text-muted'
              }`}
            >
              {METRIC_LABELS[m]}
            </button>
          ))}
        </div>
        {stats && <ProgressChart series={stats.series} unit={unit} />}
      </Card>

      {stats && Object.keys(stats.personal_records).length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {Object.entries(stats.personal_records).map(([key, pr]) =>
            pr ? (
              <Card key={key} className="text-center">
                <p className="text-xs uppercase text-muted">{METRIC_LABELS[key] ?? key.replace(/_/g, ' ')}</p>
                <p className="text-lg font-bold">
                  {key === 'fastest_pace' ? formatDuration(pr.value) : formatWeight(pr.value, unit)}
                </p>
                <p className="text-[11px] text-muted">{formatDate(pr.date)}</p>
              </Card>
            ) : null,
          )}
        </div>
      )}

      <Card>
        <label className="text-xs text-muted">Default rest timer (seconds)</label>
        <input
          type="number"
          defaultValue={exercise.default_rest_seconds ?? ''}
          placeholder={`${settings.default_rest_seconds} (global default)`}
          onBlur={(e) =>
            updateExercise.mutate({
              default_rest_seconds: e.target.value === '' ? null : Number(e.target.value),
            })
          }
          className="mt-1 h-10 w-full rounded-md border border-border bg-bg px-2 text-sm"
        />
      </Card>

      <div>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted">History</h2>
        <div className="space-y-2">
          {history?.items.map((item) => (
            <Link
              key={item.workout_id}
              to={`/history/${item.workout_id}`}
              title={`View the workout on ${formatDate(item.date)} this set was part of`}
              className="block rounded-xl border border-border bg-surface px-4 py-3 hover:bg-border/20"
            >
              <p className="text-xs text-muted">{formatDate(item.date)}</p>
              <p className="text-sm">
                {item.sets.map((s) => setSummary(s, settings.weight_unit)).join(', ') || item.notes}
              </p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
