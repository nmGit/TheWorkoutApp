import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useDashboard } from '../api/stats'
import { useActiveWorkout, useStartWorkout, useStrengthHistory, useWorkouts } from '../api/workouts'
import { useTemplates } from '../api/templates'
import { useAppSettings } from '../context/SettingsContext'
import { Button, Card, EmptyState, LoadingState, PageTitle } from '../components/ui'
import { formatDate, formatWeight, formatWorkoutDuration } from '../lib/format'
import { useUndo } from '../context/UndoContext'
import { StrengthMapThumb } from '../components/WorkoutMuscles'
import { StrengthChart } from '../components/StrengthChart'
import { RecencyCard } from '../components/RecencyCard'
import { GenerateWorkout } from '../components/GenerateWorkout'

export function HomePage() {
  const navigate = useNavigate()
  const { isHidden } = useUndo()
  const { data: pendingActive } = useActiveWorkout()
  const activeWorkout = pendingActive && !isHidden(`workout:${pendingActive.id}`) ? pendingActive : undefined
  const { data: dashboard, isLoading } = useDashboard()
  const { data: strengthHistory } = useStrengthHistory()
  const strengthById = new Map((strengthHistory ?? []).map((p) => [p.workout_id, p]))
  const { data: rawRecent } = useWorkouts({ status: 'completed', limit: 4 })
  const recentWorkouts = rawRecent?.filter((w) => !isHidden(`workout:${w.id}`))
  const { data: templates } = useTemplates()
  const visibleTemplates = templates?.filter((t) => !isHidden(`template:${t.id}`))
  const startWorkout = useStartWorkout()
  const settings = useAppSettings()
  const [showTemplates, setShowTemplates] = useState(false)

  const handleStartBlank = async () => {
    const workout = await startWorkout.mutateAsync(undefined)
    navigate('/workout/active', { state: { workoutId: workout.id } })
  }

  const handleStartFromTemplate = async (templateId: number) => {
    const workout = await startWorkout.mutateAsync(templateId)
    navigate('/workout/active', { state: { workoutId: workout.id } })
  }

  return (
    <div className="space-y-4">
      <PageTitle>WorkoutApp</PageTitle>

      {activeWorkout ? (
        <Card className="flex items-center justify-between border-accent bg-accent/5">
          <div>
            <p className="text-sm font-semibold text-accent">Workout in progress</p>
            <p className="text-xs text-muted">{activeWorkout.name}</p>
          </div>
          <Button onClick={() => navigate('/workout/active')} title="Re-enter your in-progress workout">
            Continue
          </Button>
        </Card>
      ) : (
        <Card className="space-y-3">
          <Button
            className="w-full"
            onClick={handleStartBlank}
            disabled={startWorkout.isPending}
            title="Start a new workout with no exercises pre-filled"
          >
            Start empty workout
          </Button>
          {visibleTemplates && visibleTemplates.length > 0 && (
            <Button
              variant="secondary"
              className="w-full"
              onClick={() => setShowTemplates((s) => !s)}
              title="Show your templates to start from one"
            >
              Start from template
            </Button>
          )}
          <GenerateWorkout />
          {showTemplates && (
            <div className="space-y-1.5 pt-1">
              {visibleTemplates?.map((t) => (
                <button
                  key={t.id}
                  onClick={() => handleStartFromTemplate(t.id)}
                  title={`Start a workout from "${t.name}"`}
                  className="flex w-full items-center justify-between rounded-lg border border-border px-3 py-2 text-left text-sm hover:bg-border/30"
                >
                  <span>{t.name}</span>
                  <span className="text-xs text-muted">{t.exercises.length} exercises</span>
                </button>
              ))}
            </div>
          )}
        </Card>
      )}

      {isLoading && <LoadingState />}

      <div>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted">Muscle recency</h2>
        <RecencyCard />
      </div>

      <div>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted">Strength over time</h2>
        <Card>
          <StrengthChart points={strengthHistory ?? []} />
        </Card>
      </div>

      <div>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted">Recent workouts</h2>
        {recentWorkouts && recentWorkouts.length === 0 ? (
          <EmptyState title="No workouts logged yet" hint="Start one above to see it here." />
        ) : (
          <Card className="divide-y divide-border p-0">
            {recentWorkouts?.map((w) => (
              <Link
                key={w.id}
                to={`/history/${w.id}`}
                title={`View "${w.name}" from ${formatDate(w.started_at)}`}
                className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-border/20"
              >
                <StrengthMapThumb strength={strengthById.get(w.id)} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{w.name}</p>
                  <p className="text-xs text-muted">
                    {[formatDate(w.started_at), formatWorkoutDuration(w.started_at, w.completed_at)]
                      .filter(Boolean)
                      .join(' · ')}
                  </p>
                </div>
                <p className="text-xs text-muted">
                  {w.exercise_count} {w.exercise_count === 1 ? 'exercise' : 'exercises'}
                </p>
              </Link>
            ))}
          </Card>
        )}
        <Link
          to="/history"
          title="View your full workout history"
          className="mt-2 block text-center text-xs font-medium text-muted hover:text-accent"
        >
          View all history →
        </Link>
      </div>

      {dashboard && (
        <>
          <div className="grid grid-cols-2 gap-3">
            <Card className="text-center">
              <p className="text-3xl font-bold text-accent">{dashboard.current_streak_weeks}</p>
              <p className="text-xs text-muted">week streak</p>
            </Card>
            <Card className="text-center">
              <p className="text-3xl font-bold">{dashboard.recent_prs.length}</p>
              <p className="text-xs text-muted">PRs this week</p>
            </Card>
          </div>

          <div>
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted">Recent PRs</h2>
            {dashboard.recent_prs.length === 0 ? (
              <EmptyState title="No PRs yet this week" hint="Log a workout to start tracking records." />
            ) : (
              <Card className="divide-y divide-border p-0">
                {dashboard.recent_prs.map((pr, i) => (
                  <Link
                    key={i}
                    to={`/exercises/${pr.exercise_id}`}
                    title={`View ${pr.exercise_name}'s exercise page`}
                    className="flex items-center justify-between px-4 py-3 hover:bg-border/20"
                  >
                    <div>
                      <p className="text-sm font-medium">{pr.exercise_name}</p>
                      <p className="text-xs text-muted">
                        {pr.metric.replace('_', ' ')} · {formatDate(pr.date)}
                      </p>
                    </div>
                    <p className="font-semibold text-accent">
                      {formatWeight(pr.value, pr.metric.includes('distance') ? settings.distance_unit : settings.weight_unit)}
                    </p>
                  </Link>
                ))}
              </Card>
            )}
          </div>
        </>
      )}
    </div>
  )
}
