import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useExerciseHistory, useExerciseTemplate } from '../api/exerciseTemplates'
import { useExerciseStats } from '../api/stats'
import { MuscleMapPair } from '../components/MuscleMap'
import { PoseImages } from '../components/PoseImages'
import { ProgressChart } from '../components/ProgressChart'
import { Badge, Card, LoadingState, PageTitle } from '../components/ui'
import { useAppSettings } from '../context/SettingsContext'
import { formatDate, formatDuration, formatWeight, setSummary } from '../lib/format'
import type { Muscle } from '@abdofallah/musclemap-js'
import type { ExerciseTemplate, MuscleSwatch } from '../types'

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
  const { data: exercise } = useExerciseTemplate(exerciseId)
  const { data: history } = useExerciseHistory(exerciseId)

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
      <div className="-mt-3 flex flex-wrap items-center gap-1.5 text-sm text-muted">
        <span>
          {exercise.muscle_group_name} · {exercise.equipment}
        </span>
        {exercise.mechanic && <Badge>{exercise.mechanic}</Badge>}
        {exercise.difficulty && <Badge>{exercise.difficulty}</Badge>}
      </div>

      {(exercise.image_urls.length > 0 || exercise.instruction_steps.length > 0) && (
        <Card className="space-y-3">
          {exercise.image_urls.length > 0 && (
            <div>
              <PoseImages urls={exercise.image_urls} alt={exercise.name} />
              {exercise.attribution && (
                <p className="mt-1 text-center text-[11px] text-muted">
                  <Attribution text={exercise.attribution} />
                </p>
              )}
            </div>
          )}
          {exercise.instruction_steps.length > 0 && (
            <div>
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted">
                How to perform it
              </h2>
              <ol className="list-decimal space-y-1.5 pl-5 text-sm">
                {exercise.instruction_steps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </div>
          )}
          {exercise.tips.length > 0 && (
            <div>
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted">Tips</h2>
              <ul className="list-disc space-y-1 pl-5 text-sm">
                {exercise.tips.map((tip, i) => (
                  <li key={i}>{tip}</li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {(exercise.primary_muscles.length > 0 || exercise.secondary_muscles.length > 0) && (
        <Card className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Muscles worked</h2>
          <BodyMaps exercise={exercise} />
          <MuscleRow label="Primary" muscles={exercise.primary_muscles} groupId={exercise.muscle_group_id} primary />
          <MuscleRow label="Secondary" muscles={exercise.secondary_muscles} groupId={exercise.muscle_group_id} />
        </Card>
      )}

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

/** Front and back body diagrams highlighting this exercise's muscles. Tapping a
 * region opens the exercise library filtered to that muscle. */
function BodyMaps({ exercise }: { exercise: ExerciseTemplate }) {
  const navigate = useNavigate()

  const openLibraryFor = (region: Muscle) => {
    // Primary muscles come first, so a region shared by a primary and a secondary opens the primary.
    const muscle = [...exercise.primary_muscles, ...exercise.secondary_muscles].find((m) =>
      m.regions.includes(region),
    )
    if (!muscle) return
    const params = new URLSearchParams()
    if (exercise.muscle_group_id !== null) params.set('group', String(exercise.muscle_group_id))
    params.set('muscle', muscle.slug)
    navigate(`/exercises?${params.toString()}`)
  }

  return (
    <MuscleMapPair
      primary={exercise.primary_muscles.flatMap((m) => m.regions)}
      secondary={exercise.secondary_muscles.flatMap((m) => m.regions)}
      onRegionClick={openLibraryFor}
      showLabels
    />
  )
}

/** Each muscle opens the exercise library filtered to it, within this exercise's muscle group. */
function MuscleRow({
  label,
  muscles,
  groupId,
  primary = false,
}: {
  label: string
  muscles: MuscleSwatch[]
  groupId: number | null
  primary?: boolean
}) {
  if (muscles.length === 0) return null
  const libraryLink = (m: MuscleSwatch) => {
    const params = new URLSearchParams()
    if (groupId !== null) params.set('group', String(groupId))
    params.set('muscle', m.slug)
    return `/exercises?${params.toString()}`
  }
  return (
    <div>
      <p className="mb-1.5 text-xs text-muted">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {muscles.map((m) => (
          <Link
            key={m.slug}
            to={libraryLink(m)}
            title={`See exercises that work ${m.name}`}
            className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
              primary ? 'bg-accent/15 text-accent' : 'bg-border/50 text-muted'
            }`}
          >
            {m.name}
          </Link>
        ))}
      </div>
    </div>
  )
}

/** Dataset attributions embed a URL ("© Gym visual — https://gymvisual.com/"); show it as a link. */
function Attribution({ text }: { text: string }) {
  return (
    <>
      {text.split(/(https?:\/\/\S+)/g).map((part, i) =>
        /^https?:\/\//.test(part) ? (
          <a key={i} href={part} target="_blank" rel="noreferrer" className="underline">
            {part.replace(/^https?:\/\//, '').replace(/\/$/, '')}
          </a>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  )
}
