import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  useActiveWorkout,
  useAddSet,
  useAddWorkoutExercise,
  useDeleteSet,
  useDeleteWorkout,
  useRemoveWorkoutExercise,
  useReorderWorkoutExercises,
  useUpdateSet,
  useUpdateWorkout,
} from '../api/workouts'
import { useExerciseHistory } from '../api/exerciseTemplates'
import { useTemplate, useUpdateTemplate, type TemplateExerciseInput } from '../api/templates'
import { ExercisePicker } from '../components/ExercisePicker'
import { SetRow } from '../components/SetRow'
import { Button, Card, DragHandle, EmptyState, LoadingState, ViewExerciseButton } from '../components/ui'
import { useAppSettings } from '../context/SettingsContext'
import { useGlobalRestTimer } from '../context/RestTimerContext'
import { useDragReorder } from '../hooks/useDragReorder'
import { formatElapsed } from '../lib/format'
import type { ExerciseTemplate, Workout, WorkoutExercise, WorkoutSet } from '../types'

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
  const reorderExercises = useReorderWorkoutExercises(workout?.id ?? -1)
  const { data: template } = useTemplate(workout?.template_id ?? undefined)
  const updateTemplate = useUpdateTemplate(workout?.template_id ?? -1)
  const timer = useGlobalRestTimer()

  const dragReorder = useDragReorder(
    workout?.exercises ?? [],
    (we) => we.id,
    (newOrder) => reorderExercises.mutate(newOrder.map((we) => we.id)),
  )

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
    // Offer to propagate a reordering back to the source template -- but
    // only when the workout still has exactly the template's exercises,
    // just in a different order. If exercises were also added/removed
    // relative to the template, that's a different (and more ambiguous)
    // kind of drift than "reordered", so it's left alone rather than
    // guessing at merging membership too.
    if (template && workout.template_id) {
      const workoutOrder = workout.exercises.map((we) => we.exercise_id)
      const templateOrder = template.exercises.map((te) => te.exercise_id)
      const sameSet = [...workoutOrder].sort().join(',') === [...templateOrder].sort().join(',')
      const sameOrder = workoutOrder.join(',') === templateOrder.join(',')
      if (sameSet && !sameOrder) {
        const propagate = confirm(
          `Apply this exercise order to "${template.name}" too? Choose Cancel to keep it just for this workout.`,
        )
        if (propagate) {
          const reordered: TemplateExerciseInput[] = workoutOrder.map((exerciseId) => {
            const te = template.exercises.find((t) => t.exercise_id === exerciseId)!
            return {
              exercise_id: te.exercise_id,
              target_sets: te.target_sets,
              target_reps: te.target_reps,
              target_weight: te.target_weight,
            }
          })
          await updateTemplate.mutateAsync({ exercises: reordered })
        }
      }
    }

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
          <div key={we.id} ref={dragReorder.getItemRef(we.id)}>
            <ExerciseBlock
              workout={workout}
              workoutExercise={we}
              handleProps={dragReorder.getHandleProps(we.id)}
              isDragging={dragReorder.isBeingDragged(we.id)}
            />
          </div>
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
          onSelect={async (exercise: ExerciseTemplate) => {
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

/** The ghost text for a set's rest field: the rest of the nearest earlier set
 * in this exercise (so changing one set's rest changes the suggestion for
 * every set after it), else what was used for this set position last time,
 * else the last rest used last time, else the app-wide default. */
function restGhostSeconds(sets: WorkoutSet[], index: number, previousSets: WorkoutSet[], fallback: number): number {
  for (let j = index - 1; j >= 0; j--) {
    if (sets[j].rest_seconds !== null) return sets[j].rest_seconds as number
  }
  const lastTime = previousSets[index]?.rest_seconds
  if (lastTime != null) return lastTime
  for (let j = previousSets.length - 1; j >= 0; j--) {
    if (previousSets[j].rest_seconds !== null) return previousSets[j].rest_seconds as number
  }
  return fallback
}

function ExerciseBlock({
  workout,
  workoutExercise,
  handleProps,
  isDragging,
}: {
  workout: Workout
  workoutExercise: WorkoutExercise
  handleProps: Record<string, unknown>
  isDragging: boolean
}) {
  const settings = useAppSettings()
  const timer = useGlobalRestTimer()
  const addSet = useAddSet(workout.id)
  const updateSet = useUpdateSet(workout.id)
  const deleteSet = useDeleteSet(workout.id)
  const removeExercise = useRemoveWorkoutExercise(workout.id)
  const { data: history } = useExerciseHistory(workoutExercise.exercise_id)

  const previousSets: WorkoutSet[] = history?.items.find((item) => item.workout_id !== workout.id)?.sets ?? []
  const trackingType = workoutExercise.tracking_type ?? 'weight_reps'

  const restGhost = (index: number) =>
    restGhostSeconds(workoutExercise.sets, index, previousSets, settings.default_rest_seconds)

  const handleToggleComplete = (set: WorkoutSet, index: number) => {
    const nextCompleted = !set.completed
    if (!nextCompleted) {
      updateSet.mutate({ setId: set.id, data: { completed: false } })
      return
    }
    // The rest is the set's own value if it has one, else its ghost value.
    // Completing the set saves that value into the set so the box fills in
    // (and later sets' ghost text follows it).
    const restSeconds = set.rest_seconds ?? restGhost(index)
    updateSet.mutate({
      setId: set.id,
      data: set.rest_seconds === null ? { completed: true, rest_seconds: restSeconds } : { completed: true },
    })
    timer.start(restSeconds, set.id)
  }

  const handleChange = (set: WorkoutSet, index: number, patch: Partial<WorkoutSet>) => {
    updateSet.mutate({ setId: set.id, data: patch })
    // Changing the rest of the set whose timer is running re-targets that
    // timer, keeping the time already elapsed. Clearing the field falls
    // back to the ghost value.
    if ('rest_seconds' in patch && timer.isRunning && timer.setId === set.id) {
      timer.setDuration(patch.rest_seconds ?? restGhost(index))
    }
  }

  return (
    <Card className={isDragging ? 'scale-[1.02] shadow-lg' : ''}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1">
          <DragHandle handleProps={handleProps} isDragging={isDragging} />
          <h3 className="min-w-0 truncate font-semibold">{workoutExercise.exercise_name}</h3>
        </div>
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
            previousSet={previousSets[i]}
            restGhostSeconds={restGhost(i)}
            onChange={(patch) => handleChange(set, i, patch)}
            onToggleComplete={() => handleToggleComplete(set, i)}
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
