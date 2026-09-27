import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  useActiveWorkout,
  useAddSet,
  useAddWorkoutExercise,
  useDeleteSet,
  useDeleteWorkout,
  useRemoveWorkoutExercise,
  useUpdateSet,
  useUpdateWorkout,
} from '../api/workouts'
import { useExercise, useExerciseHistory } from '../api/exercises'
import { ExercisePicker } from '../components/ExercisePicker'
import { SetRow } from '../components/SetRow'
import { Button, Card, EmptyState, LoadingState, ViewExerciseButton } from '../components/ui'
import { useAppSettings } from '../context/SettingsContext'
import { useGlobalRestTimer } from '../context/RestTimerContext'
import { formatElapsed, setSummary } from '../lib/format'
import type { Exercise, Workout, WorkoutExercise, WorkoutSet } from '../types'

export function ActiveWorkoutPage() {
  const navigate = useNavigate()
  const { data: workout, isLoading } = useActiveWorkout()
  const [pickerOpen, setPickerOpen] = useState(false)
  const [elapsedTick, setElapsedTick] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setElapsedTick((t) => t + 1), 30_000)
    return () => clearInterval(id)
  }, [])

  const updateWorkout = useUpdateWorkout(workout?.id ?? -1)
  const deleteWorkout = useDeleteWorkout()
  const addExercise = useAddWorkoutExercise(workout?.id ?? -1)
  const timer = useGlobalRestTimer()

  if (isLoading) return <LoadingState />

  if (!workout) {
    return (
      <EmptyState
        title="No workout in progress"
        hint="Start one from the home screen."
        action={
          <Button onClick={() => navigate('/')} variant="secondary" title="Go to the home screen">
            Go home
          </Button>
        }
      />
    )
  }

  const handleFinish = async () => {
    await updateWorkout.mutateAsync({ finish: true })
    timer.clear()
    navigate(`/history/${workout.id}`)
  }

  const handleDiscard = async () => {
    if (!confirm('Discard this workout? This cannot be undone.')) return
    await deleteWorkout.mutateAsync(workout.id)
    timer.clear()
    navigate('/')
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <NameEditor workout={workout} onSave={(name) => updateWorkout.mutate({ name })} />
          <p key={elapsedTick} className="text-sm text-muted">
            {formatElapsed(workout.started_at)} elapsed
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button
            onClick={handleDiscard}
            title="Discard this workout permanently"
            className="px-2 py-2 text-sm font-medium text-danger"
          >
            Discard
          </button>
          <Button
            onClick={handleFinish}
            disabled={updateWorkout.isPending}
            title="Finish and save this workout"
            className="px-3"
          >
            Finish
          </Button>
        </div>
      </div>

      {workout.exercises.length === 0 && (
        <EmptyState title="No exercises yet" hint="Add your first exercise to start logging sets." />
      )}

      <div className="space-y-3">
        {workout.exercises.map((we) => (
          <ExerciseBlock key={we.id} workout={workout} workoutExercise={we} />
        ))}
      </div>

      <Button
        variant="secondary"
        className="w-full"
        onClick={() => setPickerOpen(true)}
        title="Add an exercise to this workout"
      >
        + Add exercise
      </Button>

      {pickerOpen && (
        <ExercisePicker
          onClose={() => setPickerOpen(false)}
          onSelect={async (exercise: Exercise) => {
            await addExercise.mutateAsync(exercise.id)
            setPickerOpen(false)
          }}
        />
      )}
    </div>
  )
}

function NameEditor({ workout, onSave }: { workout: Workout; onSave: (name: string) => void }) {
  const [value, setValue] = useState(workout.name)
  useEffect(() => setValue(workout.name), [workout.name])
  return (
    <input
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onBlur={() => value.trim() && value !== workout.name && onSave(value.trim())}
      className="-ml-1 w-full min-w-0 rounded px-1 text-xl font-bold focus:bg-border/30 focus:outline-none"
    />
  )
}

function ExerciseBlock({ workout, workoutExercise }: { workout: Workout; workoutExercise: WorkoutExercise }) {
  const settings = useAppSettings()
  const timer = useGlobalRestTimer()
  const addSet = useAddSet(workout.id)
  const updateSet = useUpdateSet(workout.id)
  const deleteSet = useDeleteSet(workout.id)
  const removeExercise = useRemoveWorkoutExercise(workout.id)
  const { data: history } = useExerciseHistory(workoutExercise.exercise_id)
  const { data: exercise } = useExercise(workoutExercise.exercise_id)

  const previousSets: WorkoutSet[] = history?.items.find((item) => item.workout_id !== workout.id)?.sets ?? []
  const trackingType = workoutExercise.tracking_type ?? 'weight_reps'

  const handleToggleComplete = (set: WorkoutSet) => {
    const nextCompleted = !set.completed
    updateSet.mutate({ setId: set.id, data: { completed: nextCompleted } })
    if (nextCompleted) {
      const restSeconds = exercise?.default_rest_seconds ?? settings.default_rest_seconds
      timer.start(restSeconds)
    }
  }

  return (
    <Card>
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="min-w-0 truncate font-semibold">{workoutExercise.exercise_name}</h3>
        <div className="flex shrink-0 items-center gap-1">
          <ViewExerciseButton exerciseId={workoutExercise.exercise_id} />
          <button
            onClick={() => removeExercise.mutate(workoutExercise.id)}
            title="Remove this exercise from the workout"
            className="px-1 text-xs text-muted hover:text-danger"
          >
            Remove
          </button>
        </div>
      </div>

      <div className="space-y-0.5">
        {workoutExercise.sets.map((set, i) => (
          <SetRow
            key={set.id}
            set={set}
            index={i}
            trackingType={trackingType}
            weightUnit={settings.weight_unit}
            previousLabel={previousSets[i] ? setSummary(previousSets[i], settings.weight_unit) : undefined}
            onChange={(patch) => updateSet.mutate({ setId: set.id, data: patch })}
            onToggleComplete={() => handleToggleComplete(set)}
            onDelete={() => deleteSet.mutate(set.id)}
          />
        ))}
      </div>

      <button
        onClick={() => addSet.mutate(workoutExercise.id)}
        title="Add another set, copied from the last one"
        className="mt-2 w-full rounded-lg border border-dashed border-border py-2 text-sm font-medium text-muted hover:bg-border/20"
      >
        + Add set
      </button>
    </Card>
  )
}
