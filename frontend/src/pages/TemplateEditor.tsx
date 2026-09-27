import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTemplate, useUpdateTemplate, type TemplateExerciseInput } from '../api/templates'
import { ExercisePicker } from '../components/ExercisePicker'
import { Button, Card, LoadingState, PageTitle } from '../components/ui'
import type { Exercise, TemplateExercise } from '../types'

export function TemplateEditorPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const templateId = Number(id)
  const { data: template, isLoading } = useTemplate(templateId)
  const updateTemplate = useUpdateTemplate(templateId)

  const [name, setName] = useState('')
  const [exercises, setExercises] = useState<TemplateExercise[]>([])
  const [pickerOpen, setPickerOpen] = useState(false)

  useEffect(() => {
    if (template) {
      setName(template.name)
      setExercises(template.exercises)
    }
  }, [template])

  if (isLoading || !template) return <LoadingState />

  const persist = (next: TemplateExercise[]) => {
    setExercises(next)
    const payload: TemplateExerciseInput[] = next.map((e) => ({
      exercise_id: e.exercise_id,
      target_sets: e.target_sets,
      target_reps: e.target_reps,
      target_weight: e.target_weight,
    }))
    updateTemplate.mutate({ exercises: payload })
  }

  const updateExercise = (index: number, patch: Partial<TemplateExercise>) => {
    const next = exercises.map((e, i) => (i === index ? { ...e, ...patch } : e))
    persist(next)
  }

  const removeExercise = (index: number) => {
    persist(exercises.filter((_, i) => i !== index))
  }

  const move = (index: number, dir: -1 | 1) => {
    const target = index + dir
    if (target < 0 || target >= exercises.length) return
    const next = [...exercises]
    ;[next[index], next[target]] = [next[target], next[index]]
    persist(next)
  }

  const addExercise = (exercise: Exercise) => {
    persist([
      ...exercises,
      {
        id: -Date.now(),
        exercise_id: exercise.id,
        exercise_name: exercise.name,
        position: exercises.length,
        target_sets: 3,
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

      <div className="space-y-2">
        {exercises.map((ex, i) => (
          <Card key={ex.id} className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="font-medium">{ex.exercise_name}</p>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => move(i, -1)}
                  disabled={i === 0}
                  className="text-muted hover:text-fg disabled:opacity-30"
                  title="Move up"
                  aria-label="Move up"
                >
                  ↑
                </button>
                <button
                  onClick={() => move(i, 1)}
                  disabled={i === exercises.length - 1}
                  className="text-muted hover:text-fg disabled:opacity-30"
                  title="Move down"
                  aria-label="Move down"
                >
                  ↓
                </button>
                <button
                  onClick={() => removeExercise(i)}
                  title={`Remove ${ex.exercise_name} from this template`}
                  className="ml-2 text-xs text-muted hover:text-danger"
                >
                  Remove
                </button>
              </div>
            </div>
            <div className="flex gap-2">
              <LabeledInput
                label="Sets"
                value={ex.target_sets?.toString() ?? ''}
                onCommit={(v) => updateExercise(i, { target_sets: v === '' ? null : Number(v) })}
              />
              <LabeledInput
                label="Reps"
                value={ex.target_reps ?? ''}
                onCommit={(v) => updateExercise(i, { target_reps: v || null })}
              />
              <LabeledInput
                label="Weight"
                value={ex.target_weight?.toString() ?? ''}
                onCommit={(v) => updateExercise(i, { target_weight: v === '' ? null : Number(v) })}
              />
            </div>
          </Card>
        ))}
      </div>

      <Button
        variant="secondary"
        className="w-full"
        onClick={() => setPickerOpen(true)}
        title="Add an exercise to this template"
      >
        + Add exercise
      </Button>

      {pickerOpen && <ExercisePicker onClose={() => setPickerOpen(false)} onSelect={addExercise} />}
    </div>
  )
}

function LabeledInput({ label, value, onCommit }: { label: string; value: string; onCommit: (value: string) => void }) {
  const [local, setLocal] = useState(value)
  useEffect(() => setLocal(value), [value])
  return (
    <label className="flex-1 text-xs text-muted">
      {label}
      <input
        value={local}
        onChange={(e) => setLocal(e.target.value)}
        onBlur={() => onCommit(local)}
        className="mt-0.5 h-9 w-full rounded-md border border-border bg-bg px-2 text-sm text-fg"
      />
    </label>
  )
}
