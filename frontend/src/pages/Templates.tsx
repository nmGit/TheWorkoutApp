import { useNavigate } from 'react-router-dom'
import { useCreateTemplate, useDeleteTemplate, useTemplates } from '../api/templates'
import { useActiveWorkout, useStartWorkout } from '../api/workouts'
import { Button, Card, EmptyState, LoadingState, PageTitle } from '../components/ui'

export function TemplatesPage() {
  const navigate = useNavigate()
  const { data: templates, isLoading } = useTemplates()
  const createTemplate = useCreateTemplate()
  const deleteTemplate = useDeleteTemplate()
  const startWorkout = useStartWorkout()
  const { data: activeWorkout } = useActiveWorkout()

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

      {templates?.length === 0 ? (
        <EmptyState title="No templates yet" hint="Create a routine to start workouts with one tap." />
      ) : (
        <div className="space-y-3">
          {templates?.map((t) => (
            <Card key={t.id} className="space-y-2">
              <div className="flex items-start justify-between">
                <button className="text-left" onClick={() => navigate(`/templates/${t.id}`)} title={`Edit "${t.name}"`}>
                  <p className="font-semibold">{t.name}</p>
                  <p className="text-xs text-muted">
                    {t.exercises.map((e) => e.exercise_name).join(', ') || 'No exercises yet'}
                  </p>
                </button>
                <button
                  onClick={() => deleteTemplate.mutate(t.id)}
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
