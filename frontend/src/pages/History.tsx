import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useStrengthHistory, useWorkouts } from '../api/workouts'
import { Card, EmptyState, LoadingState, PageTitle } from '../components/ui'
import { formatDate, formatWorkoutDuration } from '../lib/format'
import { useUndo } from '../context/UndoContext'
import { StrengthMapThumb } from '../components/WorkoutMuscles'

const WEEKS = 32

/** A calendar day as YYYY-MM-DD in the viewer's local timezone. Both the workouts and
 * the heatmap cells must use local days; mixing in UTC shifts days by a timezone's offset. */
function localDateKey(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function HistoryPage() {
  const { data: rawWorkouts, isLoading } = useWorkouts({ status: 'completed', limit: 200 })
  const { isHidden } = useUndo()
  const workouts = rawWorkouts?.filter((w) => !isHidden(`workout:${w.id}`))
  const { data: history } = useStrengthHistory()
  const strengthById = useMemo(() => new Map((history ?? []).map((p) => [p.workout_id, p])), [history])

  const trainedDays = useMemo(() => {
    const set = new Set<string>()
    for (const w of workouts ?? []) set.add(localDateKey(new Date(w.started_at)))
    return set
  }, [workouts])

  if (isLoading) return <LoadingState />

  return (
    <div className="space-y-4">
      <PageTitle>History</PageTitle>

      <Card>
        <Heatmap trainedDays={trainedDays} />
      </Card>

      {workouts?.length === 0 ? (
        <EmptyState title="No workouts yet" hint="Finish a workout to see it here." />
      ) : (
        <div className="space-y-2">
          {workouts?.map((w) => (
            <Link
              key={w.id}
              to={`/history/${w.id}`}
              title={`View "${w.name}" from ${formatDate(w.started_at)}`}
              className="flex items-center justify-between gap-3 rounded-xl border border-border bg-surface px-4 py-3 hover:bg-border/20"
            >
              <StrengthMapThumb strength={strengthById.get(w.id)} />
              <div className="min-w-0 flex-1">
                <p className="font-medium">{w.name}</p>
                <p className="text-xs text-muted">
                  {[formatDate(w.started_at), formatWorkoutDuration(w.started_at, w.completed_at)]
                    .filter(Boolean)
                    .join(' · ')}
                  {w.template_name ? ` · ${w.template_name}` : ''}
                </p>
              </div>
              <p className="text-sm text-muted">
                {w.exercise_count} {w.exercise_count === 1 ? 'exercise' : 'exercises'}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

function Heatmap({ trainedDays }: { trainedDays: Set<string> }) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  // Start on the Sunday that begins the oldest week, so every column runs Sun → Sat
  const start = new Date(today)
  start.setDate(start.getDate() - today.getDay() - (WEEKS - 1) * 7)

  const weeks: Date[][] = []
  const cursor = new Date(start)
  for (let w = 0; w < WEEKS; w++) {
    const days: Date[] = []
    for (let d = 0; d < 7; d++) {
      days.push(new Date(cursor))
      cursor.setDate(cursor.getDate() + 1)
    }
    weeks.push(days)
  }

  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase text-muted">Last {WEEKS} weeks</p>
      <div className="flex gap-1">
        {weeks.map((days, wi) => (
          <div key={wi} className="flex min-w-0 flex-1 flex-col gap-1">
            {days.map((day, di) => {
              const key = localDateKey(day)
              const trained = trainedDays.has(key)
              const future = day > today
              const isToday = day.getTime() === today.getTime()
              return (
                <div
                  key={di}
                  title={isToday ? `${key} (today)` : key}
                  className={`aspect-square w-full rounded-sm ${
                    future ? 'bg-transparent' : trained ? 'bg-accent' : 'bg-border/60'
                  } ${isToday ? 'ring-2 ring-fg ring-offset-1 ring-offset-surface' : ''}`}
                />
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}
