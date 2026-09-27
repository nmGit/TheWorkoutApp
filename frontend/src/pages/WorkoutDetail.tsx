import { useNavigate, useParams } from 'react-router-dom'
import { useExercise } from '../api/exercises'
import { useExerciseStats } from '../api/stats'
import { useCreateTemplateFromWorkout } from '../api/templates'
import { useDeleteSet, useDeleteWorkout, useUpdateSet, useWorkout } from '../api/workouts'
import { SetRow } from '../components/SetRow'
import { Badge, Button, Card, LoadingState, PageTitle, ViewExerciseButton } from '../components/ui'
import { useAppSettings } from '../context/SettingsContext'
import { formatDate } from '../lib/format'
import type { Workout, WorkoutExercise } from '../types'

export function WorkoutDetailPage() {
  const { workoutId } = useParams()
  const navigate = useNavigate()
  const id = Number(workoutId)
  const { data: workout, isLoading } = useWorkout(id)
  const createTemplate = useCreateTemplateFromWorkout()
  const deleteWorkout = useDeleteWorkout()

  if (isLoading || !workout) return <LoadingState />

  const handleSaveAsTemplate = async () => {
    const template = await createTemplate.mutateAsync(workout.id)
    navigate(`/templates/${template.id}`)
  }

  const handleDelete = async () => {
    if (!confirm('Delete this workout permanently?')) return
    await deleteWorkout.mutateAsync(workout.id)
    navigate('/history')
  }

  return (
    <div className="space-y-4">
      <PageTitle>{workout.name}</PageTitle>
      <p className="-mt-3 text-sm text-muted">
        {formatDate(workout.started_at)}
        {workout.template_name ? ` · from ${workout.template_name}` : ''}
      </p>

      <div className="space-y-3">
        {workout.exercises.map((we) => (
          <ExerciseSection key={we.id} workout={workout} workoutExercise={we} />
        ))}
      </div>

      <div className="flex gap-2">
        <Button
          variant="secondary"
          className="flex-1"
          onClick={handleSaveAsTemplate}
          disabled={createTemplate.isPending}
          title="Create a reusable template from this workout"
        >
          Save as template
        </Button>
        <Button variant="ghost" className="text-danger" onClick={handleDelete} title="Delete this workout permanently">
          Delete
        </Button>
      </div>
    </div>
  )
}

function ExerciseSection({ workout, workoutExercise }: { workout: Workout; workoutExercise: WorkoutExercise }) {
  const settings = useAppSettings()
  const updateSet = useUpdateSet(workout.id)
  const deleteSet = useDeleteSet(workout.id)
  const { data: exercise } = useExercise(workoutExercise.exercise_id)
  const { data: stats } = useExerciseStats(workoutExercise.exercise_id)

  const isPrWorkout = stats
    ? Object.values(stats.personal_records).some((pr) => pr?.workout_id === workout.id)
    : false

  return (
    <Card>
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <h3 className="truncate font-semibold">{workoutExercise.exercise_name}</h3>
          {isPrWorkout && <Badge tone="accent">PR</Badge>}
          {exercise?.equipment && <Badge>{exercise.equipment}</Badge>}
        </div>
        <ViewExerciseButton exerciseId={workoutExercise.exercise_id} />
      </div>
      {workoutExercise.notes && <p className="mb-2 text-xs text-muted">{workoutExercise.notes}</p>}
      <div className="space-y-0.5">
        {workoutExercise.sets.map((set, i) => (
          <SetRow
            key={set.id}
            set={set}
            index={i}
            trackingType={workoutExercise.tracking_type ?? 'weight_reps'}
            weightUnit={settings.weight_unit}
            onChange={(patch) => updateSet.mutate({ setId: set.id, data: patch })}
            onToggleComplete={() => updateSet.mutate({ setId: set.id, data: { completed: !set.completed } })}
            onDelete={() => deleteSet.mutate(set.id)}
          />
        ))}
      </div>
    </Card>
  )
}
