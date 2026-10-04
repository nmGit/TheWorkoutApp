import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreateTemplate, useDeleteTemplate, useTemplates } from '../api/templates'
import { useActiveWorkout, useStartWorkout, useStrengthHistory } from '../api/workouts'
import { Button, Card, EmptyState, LoadingState, PageTitle } from '../components/ui'
import { useUndo } from '../context/UndoContext'
import type { StrengthPoint } from '../types'
import { TemplateMapThumb } from '../components/WorkoutMuscles'

export function TemplatesPage() {
  const navigate = useNavigate()
  const { data: templates, isLoading } = useTemplates()
  const createTemplate = useCreateTemplate()
  const deleteTemplate = useDeleteTemplate()
  const startWorkout = useStartWorkout()
  const { deleteWithUndo, isHidden } = useUndo()
  const { data: pendingActive } = useActiveWorkout()
  const activeWorkout = pendingActive && !isHidden(`workout:${pendingActive.id}`) ? pendingActive : undefined
  const visibleTemplates = templates?.filter((t) => !isHidden(`template:${t.id}`))
  const { data: history } = useStrengthHistory()
  // Points are oldest first, so the last one for a template is its latest instance.
  const latestByTemplate = useMemo(() => {
    const map = new Map<number, StrengthPoint>()
    for (const p of history ?? []) if (p.template_id !== null) map.set(p.template_id, p)
    return map
  }, [history])

  const handleCreate = async () => {
    const template = await createTemplate.mutateAsync({ name: 'New Template', exercises: [] })
    navigate(`/templates/${template.id}`)
  }

  const handleStart = async (templateId: number) => {
    if (activeWorkout) {
      navigate('/workout/active')
      return
    }
    await startWorkout.mutateAsync(templateId)
    navigate('/workout/active')
  }

  if (isLoading) return <LoadingState />

  return (
    <div className="space-y-4">
      <PageTitle
        action={
          <Button onClick={handleCreate} disabled={createTemplate.isPending} title="Create a new template">
            + New
          </Button>
        }
      >
        Templates
      </PageTitle>

      {visibleTemplates?.length === 0 ? (
        <EmptyState title="No templates yet" hint="Create a routine to start workouts with one tap." />
      ) : (
        <div className="space-y-3">
          {visibleTemplates?.map((t) => (
            <Card key={t.id} className="space-y-2">
              <div className="flex items-start gap-3">
                <TemplateMapThumb muscles={t.muscles} latest={latestByTemplate.get(t.id)} />
                <button
                  className="min-w-0 flex-1 text-left"
                  onClick={() => navigate(`/templates/${t.id}`)}
                  title={`Edit "${t.name}"`}
                >
                  <p className="font-semibold">{t.name}</p>
                  <p className="text-xs text-muted">
                    {t.exercises.map((e) => e.exercise_name).join(', ') || 'No exercises yet'}
                  </p>
                </button>
                <button
                  onClick={() =>
                    deleteWithUndo({
                      message: `Deleted "${t.name}"`,
                      hideKey: `template:${t.id}`,
                      commit: () => deleteTemplate.mutateAsync(t.id),
                    })
                  }
                  title={`Delete template "${t.name}"`}
                  className="text-xs text-muted hover:text-danger"
                >
                  Delete
                </button>
              </div>
              <Button
                variant="secondary"
                className="w-full"
                onClick={() => handleStart(t.id)}
                title={activeWorkout ? 'A workout is already active; go continue it' : `Start a workout from "${t.name}"`}
              >
                Start workout
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
