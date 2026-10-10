import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useStrengthHistory } from '../api/workouts'
import { useTemplate, useUpdateTemplate, type TemplateExerciseInput } from '../api/templates'
import { ExerciseCard } from '../components/ExerciseCard'
import { ExerciseList } from '../components/ExerciseList'
import { ExercisePicker } from '../components/ExercisePicker'
import { PlanSets } from '../components/PlanSets'
import { TemplateMusclesHeader } from '../components/WorkoutMuscles'
import { Button, DragHandle, LoadingState, PageTitle, ViewExerciseButton } from '../components/ui'
import { useUndo } from '../context/UndoContext'
import { useDragReorder } from '../hooks/useDragReorder'
import type { ExerciseTemplate, TemplateExercise } from '../types'

export function TemplateEditorPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const templateId = Number(id)
  const { data: template, isLoading } = useTemplate(templateId)
  const updateTemplate = useUpdateTemplate(templateId)
  const { data: history } = useStrengthHistory()
  const { showUndo } = useUndo()

  const [name, setName] = useState('')
  const [exercises, setExercises] = useState<TemplateExercise[]>([])
  const [pickerOpen, setPickerOpen] = useState(false)

  // History is oldest first, so the last point for this template is its latest completed workout.
  const latest = useMemo(
    () => (history ?? []).filter((p) => p.template_id === templateId).at(-1),
    [history, templateId],
  )

  useEffect(() => {
    if (template) {
      setName(template.name)
      setExercises(template.exercises)
    }
  }, [template])

  const persist = (next: TemplateExercise[]) => {
    setExercises(next)
    // The plan is the set counts and the rep range. Weights come from the last session and progress from it.
    const payload: TemplateExerciseInput[] = next.map((e) => ({
      exercise_id: e.exercise_id,
      target_sets: e.target_sets,
      warmup_sets: e.warmup_sets,
      drop_sets: e.drop_sets,
      target_reps: e.target_reps,
    }))
    updateTemplate.mutate({ exercises: payload })
  }

  const dragReorder = useDragReorder(exercises, (ex) => ex.id, persist)

  if (isLoading || !template) return <LoadingState />

  const updateExercise = (index: number, patch: Partial<TemplateExercise>) => {
    persist(exercises.map((e, i) => (i === index ? { ...e, ...patch } : e)))
  }

  const removeExercise = (index: number) => {
    const previous = exercises
    persist(exercises.filter((_, i) => i !== index))
    showUndo({
      message: `Removed ${previous[index].exercise_name ?? 'exercise'}`,
      onUndo: () => persist(previous),
    })
  }

  const addExercise = (exercise: ExerciseTemplate) => {
    persist([
      ...exercises,
      {
        id: -Date.now(),
        exercise_id: exercise.id,
        exercise_name: exercise.name,
        position: exercises.length,
        target_sets: 3,
        warmup_sets: 0,
        drop_sets: 0,
        target_reps: null,
        target_weight: null,
      },
    ])
    setPickerOpen(false)
  }

  return (
    <div className="space-y-4">
      <PageTitle
        action={
          <Button variant="secondary" onClick={() => navigate('/templates')} title="Done editing, back to templates">
            Done
          </Button>
        }
      >
        Edit template
      </PageTitle>

      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        onBlur={() => name.trim() && updateTemplate.mutate({ name: name.trim() })}
        className="w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-lg font-semibold"
        placeholder="Template name"
      />

      <TemplateMusclesHeader muscles={template.muscles} latest={latest} />

      <ExerciseList
        items={exercises}
        dragReorder={dragReorder}
        className="space-y-2"
        renderCard={(ex, i) => (
          <ExerciseCard
            title={ex.exercise_name}
            dragging={dragReorder.isBeingDragged(ex.id)}
            leading={<DragHandle handleProps={dragReorder.getHandleProps(ex.id)} isDragging={dragReorder.isBeingDragged(ex.id)} />}
            actions={
              <>
                <ViewExerciseButton exerciseId={ex.exercise_id} />
                <button
                  onClick={() => removeExercise(i)}
                  title={`Remove ${ex.exercise_name} from this template`}
                  className="ml-1 px-1 text-xs text-muted hover:text-danger"
                >
                  Remove
                </button>
              </>
            }
          >
            <PlanSets exercise={ex} onChange={(patch) => updateExercise(i, patch)} />
          </ExerciseCard>
        )}
      />

      <Button variant="secondary" className="w-full" onClick={() => setPickerOpen(true)} title="Add an exercise to this template">
        + Add exercise
      </Button>

      {pickerOpen && <ExercisePicker onClose={() => setPickerOpen(false)} onSelect={addExercise} />}
    </div>
  )
}
