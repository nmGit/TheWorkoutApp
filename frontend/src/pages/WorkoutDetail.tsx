import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useExerciseTemplate } from '../api/exerciseTemplates'
import { useExerciseStats } from '../api/stats'
import { useCreateTemplateFromWorkout } from '../api/templates'
import { useDeleteSet, useDeleteWorkout, useUpdateSet, useWorkout } from '../api/workouts'
import { SetRow } from '../components/SetRow'
import { ExerciseCard } from '../components/ExerciseCard'
import { ExerciseList } from '../components/ExerciseList'
import { ExerciseNotesMenu, ExerciseNotesPanel, type NoteKind } from '../components/ExerciseNotes'
import { Badge, Button, LoadingState, PageTitle, ViewExerciseButton } from '../components/ui'
import { useAppSettings } from '../context/SettingsContext'
import { formatDate, formatWorkoutDuration } from '../lib/format'
import type { Workout, WorkoutExercise } from '../types'
import { useUndo } from '../context/UndoContext'
import { WorkoutMusclesHeader } from '../components/WorkoutMuscles'

export function WorkoutDetailPage() {
  const { workoutId } = useParams()
  const navigate = useNavigate()
  const id = Number(workoutId)
  const { data: workout, isLoading } = useWorkout(id)
  const createTemplate = useCreateTemplateFromWorkout()
  const deleteWorkout = useDeleteWorkout()
  const { deleteWithUndo } = useUndo()

  if (isLoading || !workout) return <LoadingState />

  const handleSaveAsTemplate = async () => {
    const template = await createTemplate.mutateAsync(workout.id)
    navigate(`/templates/${template.id}`)
  }

  const handleDelete = () => {
    deleteWithUndo({
      message: 'Workout deleted',
      hideKey: `workout:${workout.id}`,
      commit: () => deleteWorkout.mutateAsync(workout.id),
    })
    navigate('/history')
  }

  return (
    <div className="space-y-4">
      <PageTitle>{workout.name}</PageTitle>
      <p className="-mt-3 text-sm text-muted">
        {[formatDate(workout.started_at), formatWorkoutDuration(workout.started_at, workout.completed_at)]
          .filter(Boolean)
          .join(' · ')}
        {workout.template_name ? ` · from ${workout.template_name}` : ''}
      </p>

      <WorkoutMusclesHeader workoutId={workout.id} muscles={workout.muscles} />

      <ExerciseList
        items={workout.exercises}
        renderCard={(we) => <ExerciseSection workout={workout} workoutExercise={we} />}
      />

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
  const { deleteWithUndo, isHidden } = useUndo()
  const { data: exercise } = useExerciseTemplate(workoutExercise.exercise_id)
  const { data: stats } = useExerciseStats(workoutExercise.exercise_id)
  const [editingNote, setEditingNote] = useState<NoteKind | null>(null)

  const isPrWorkout = stats
    ? Object.values(stats.personal_records).some((pr) => pr?.workout_id === workout.id)
    : false

  return (
    <ExerciseCard
      title={workoutExercise.exercise_name}
      badges={
        <>
          {isPrWorkout && <Badge tone="accent">PR</Badge>}
          {exercise?.equipment && <Badge>{exercise.equipment}</Badge>}
        </>
      }
      actions={
        <>
          <ViewExerciseButton exerciseId={workoutExercise.exercise_id} />
          <ExerciseNotesMenu onChoose={setEditingNote} />
        </>
      }
      notes={
        <ExerciseNotesPanel
          workoutId={workout.id}
          workoutExercise={workoutExercise}
          editing={editingNote}
          onDone={() => setEditingNote(null)}
        />
      }
    >
      <div className="space-y-0.5">
        {workoutExercise.sets.map((set, i) =>
          isHidden(`set:${set.id}`) ? null : (
            <SetRow
              key={set.id}
              set={set}
              index={i}
              trackingType={workoutExercise.tracking_type ?? 'weight_reps'}
              weightUnit={settings.weight_unit}
              onChange={(patch) => updateSet.mutate({ setId: set.id, data: patch })}
              onToggleComplete={() => updateSet.mutate({ setId: set.id, data: { completed: !set.completed } })}
              onDelete={() =>
                deleteWithUndo({
                  message: 'Set deleted',
                  hideKey: `set:${set.id}`,
                  commit: () => deleteSet.mutateAsync(set.id),
                })
              }
            />
          ),
        )}
      </div>
    </ExerciseCard>
  )
}
