import { useEffect, useRef, useState } from 'react'
import { useExerciseTemplate, useUpdateExerciseTemplate } from '../api/exerciseTemplates'
import { useUpdateWorkoutExercise } from '../api/workouts'
import type { WorkoutExercise } from '../types'

/** "instance": this workout only. "template": every workout of this exercise. */
export type NoteKind = 'instance' | 'template'

/** The three-dot menu in an exercise's header, offering both kinds of note. */
export function ExerciseNotesMenu({ onChoose }: { onChoose: (kind: NoteKind) => void }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent) {
        if (e.key === 'Escape') setOpen(false)
        return
      }
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', close)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', close)
    }
  }, [open])

  const choose = (kind: NoteKind) => {
    setOpen(false)
    onChoose(kind)
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-muted hover:bg-border/40 ${
          open ? 'bg-border/40' : ''
        }`}
        title="Exercise notes"
        aria-label="Exercise notes"
        aria-expanded={open}
      >
        ⋯
      </button>
      {open && (
        <div className="absolute right-0 top-full z-10 mt-1 flex w-52 flex-col overflow-hidden rounded-lg border border-border bg-surface py-1 shadow-lg">
          <button
            type="button"
            onClick={() => choose('instance')}
            className="px-3 py-2 text-left text-sm text-fg hover:bg-border/40"
            title="A note for this workout only"
          >
            Note for this workout
          </button>
          <button
            type="button"
            onClick={() => choose('template')}
            className="px-3 py-2 text-left text-sm text-fg hover:bg-border/40"
            title="A note shown in every workout of this exercise: reminders, form tips"
          >
            Note for every workout
          </button>
        </div>
      )}
    </div>
  )
}

/** The notes under an exercise's header, plus the editor when one is open. Template
 * notes are green, instance notes yellow. */
export function ExerciseNotesPanel({
  workoutId,
  workoutExercise,
  editing,
  onDone,
}: {
  workoutId: number
  workoutExercise: WorkoutExercise
  editing: NoteKind | null
  onDone: () => void
}) {
  const { data: exercise } = useExerciseTemplate(workoutExercise.exercise_id)
  const updateInstance = useUpdateWorkoutExercise(workoutId)
  const updateTemplate = useUpdateExerciseTemplate(workoutExercise.exercise_id)

  const templateNote = exercise?.notes ?? null
  const instanceNote = workoutExercise.notes

  const save = async (text: string) => {
    const trimmed = text.trim()
    if (editing === 'instance') {
      await updateInstance.mutateAsync({ workoutExerciseId: workoutExercise.id, notes: trimmed })
    } else {
      await updateTemplate.mutateAsync({ notes: trimmed || null })
    }
    onDone()
  }

  return (
    <div className="mb-2 space-y-1.5">
      {editing === 'template' ? (
        <NoteEditor
          initial={templateNote ?? ''}
          tone="template"
          onSave={save}
          onCancel={onDone}
        />
      ) : (
        templateNote && <NoteBanner text={templateNote} tone="template" />
      )}
      {editing === 'instance' ? (
        <NoteEditor
          initial={instanceNote ?? ''}
          tone="instance"
          onSave={save}
          onCancel={onDone}
        />
      ) : (
        instanceNote && <NoteBanner text={instanceNote} tone="instance" />
      )}
    </div>
  )
}

const TONE = {
  template: 'border-success/30 bg-success/10',
  instance: 'border-amber-400/40 bg-amber-400/15',
}

function NoteBanner({ text, tone }: { text: string; tone: 'template' | 'instance' }) {
  return (
    <div className={`rounded-lg border px-3 py-2 text-sm ${TONE[tone]}`}>
      <p className="whitespace-pre-wrap">{text}</p>
    </div>
  )
}

function NoteEditor({
  initial,
  tone,
  onSave,
  onCancel,
}: {
  initial: string
  tone: 'template' | 'instance'
  onSave: (text: string) => Promise<void>
  onCancel: () => void
}) {
  const [text, setText] = useState(initial)
  const [saving, setSaving] = useState(false)

  const submit = async () => {
    setSaving(true)
    try {
      await onSave(text)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className={`space-y-2 rounded-lg border px-3 py-2 ${TONE[tone]}`}>
      <textarea
        autoFocus
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={3}
        placeholder={tone === 'template' ? 'Reminders, form tips…' : 'How it went, what to change…'}
        className="w-full resize-y rounded-md border border-border bg-bg px-2 py-1.5 text-sm"
      />
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="h-8 rounded-full border border-border px-3 text-sm text-muted hover:bg-border/40"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={submit}
          disabled={saving}
          className="h-8 rounded-full bg-fg px-3 text-sm font-medium text-bg hover:opacity-90 disabled:opacity-50"
        >
          Save
        </button>
      </div>
    </div>
  )
}
