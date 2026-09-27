import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useWorkouts } from '../api/workouts'
import { Card, EmptyState, LoadingState, PageTitle } from '../components/ui'
import { formatDate } from '../lib/format'

const WEEKS = 32

export function HistoryPage() {
  const { data: workouts, isLoading } = useWorkouts({ status: 'completed', limit: 200 })

  const trainedDays = useMemo(() => {
    const set = new Set<string>()
    for (const w of workouts ?? []) set.add(w.started_at.slice(0, 10))
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
              className="flex items-center justify-between rounded-xl border border-border bg-surface px-4 py-3 hover:bg-border/20"
            >
              <div>
                <p className="font-medium">{w.name}</p>
                <p className="text-xs text-muted">
                  {formatDate(w.started_at)}
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
  const start = new Date(today)
  start.setDate(start.getDate() - (WEEKS * 7 - 1) - today.getDay())

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
      <div className="flex gap-1 overflow-x-auto">
        {weeks.map((days, wi) => (
          <div key={wi} className="flex flex-col gap-1">
            {days.map((day, di) => {
              const key = day.toISOString().slice(0, 10)
              const trained = trainedDays.has(key)
              const future = day > today
              return (
                <div
                  key={di}
                  title={key}
                  className={`h-3 w-3 rounded-sm ${
                    future ? 'bg-transparent' : trained ? 'bg-accent' : 'bg-border/60'
                  }`}
                />
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}
