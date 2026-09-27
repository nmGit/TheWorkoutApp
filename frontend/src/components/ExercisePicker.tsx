import { useMemo, useState, type ReactNode } from 'react'
import { useExerciseTemplates } from '../api/exerciseTemplates'
import { useCreateExercise, useExercises, useMuscleGroups } from '../api/exercises'
import type { Exercise, ExerciseTemplate } from '../types'
import { Button } from './ui'

interface Props {
  onSelect: (exercise: Exercise) => void
  onClose: () => void
}

type Tab = 'mine' | 'templates'

export function ExercisePicker({ onSelect, onClose }: Props) {
  const [tab, setTab] = useState<Tab>('mine')
  const [query, setQuery] = useState('')
  const [muscleGroupId, setMuscleGroupId] = useState<number | undefined>(undefined)
  const { data: groups } = useMuscleGroups()
  const { data: exercises, isLoading } = useExercises({ q: query || undefined, muscleGroupId })
  const { data: templateResults, isLoading: templatesLoading } = useExerciseTemplates({
    q: query || undefined,
    limit: 30,
  })
  const createExercise = useCreateExercise()

  const grouped = useMemo(() => {
    const map = new Map<string, Exercise[]>()
    for (const ex of exercises ?? []) {
      const key = ex.muscle_group_name ?? 'Other'
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(ex)
    }
    const order = new Map((groups ?? []).map((g) => [g.name, g.display_order]))
    return new Map([...map.entries()].sort((a, b) => (order.get(a[0]) ?? 99) - (order.get(b[0]) ?? 99)))
  }, [exercises, groups])

  const canCreate = query.trim().length > 0 && exercises?.every((e) => e.name.toLowerCase() !== query.trim().toLowerCase())

  const handleCreate = async () => {
    const groupId = muscleGroupId ?? groups?.[0]?.id
    if (!groupId) return
    const created = await createExercise.mutateAsync({
      name: query.trim(),
      muscle_group_id: groupId,
      tracking_type: 'weight_reps',
    })
    onSelect(created)
  }

  const handleUseTemplate = async (template: ExerciseTemplate) => {
    const created = await createExercise.mutateAsync({ template_id: template.id })
    onSelect(created)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center" onClick={onClose}>
      <div
        className="flex max-h-[85vh] w-full max-w-xl flex-col rounded-t-2xl bg-surface sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border p-4">
          <h2 className="text-lg font-semibold">Add exercise</h2>
          <button onClick={onClose} className="text-muted" title="Close" aria-label="Close">
            ✕
          </button>
        </div>

        <div className="flex border-b border-border px-4 pt-2">
          <TabButton active={tab === 'mine'} onClick={() => setTab('mine')}>
            My exercises
          </TabButton>
          <TabButton active={tab === 'templates'} onClick={() => setTab('templates')}>
            Browse templates
          </TabButton>
        </div>

        <div className="space-y-2 border-b border-border p-4">
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={tab === 'mine' ? 'Search exercises…' : 'Search exercise templates…'}
            className="h-11 w-full rounded-lg border border-border bg-bg px-3 text-sm"
          />
          {tab === 'mine' && (
            <div className="flex flex-wrap gap-1.5">
              <FilterChip active={muscleGroupId === undefined} onClick={() => setMuscleGroupId(undefined)} title="Show all muscle groups">
                All
              </FilterChip>
              {groups?.map((g) => (
                <FilterChip
                  key={g.id}
                  active={muscleGroupId === g.id}
                  onClick={() => setMuscleGroupId(g.id)}
                  title={`Filter to ${g.name}`}
                >
                  {g.name}
                </FilterChip>
              ))}
            </div>
          )}
        </div>

        {tab === 'mine' && (
          <div className="flex-1 overflow-y-auto p-2">
            {isLoading && <p className="p-4 text-center text-sm text-muted">Loading…</p>}
            {!isLoading && exercises?.length === 0 && !canCreate && (
              <p className="p-4 text-center text-sm text-muted">No exercises found.</p>
            )}
            {[...grouped.entries()].map(([group, items]) => (
              <div key={group} className="mb-2">
                <p className="px-2 py-1 text-xs font-semibold uppercase text-muted">{group}</p>
                {items.map((ex) => (
                  <button
                    key={ex.id}
                    onClick={() => onSelect(ex)}
                    title={`Select ${ex.name}`}
                    className="flex w-full items-center justify-between rounded-lg px-2 py-2.5 text-left hover:bg-border/30"
                  >
                    <span className="text-sm">{ex.name}</span>
                    {ex.last_performed && (
                      <span className="text-xs text-muted">{ex.last_performed.summary}</span>
                    )}
                  </button>
                ))}
              </div>
            ))}

            {canCreate && (
              <div className="p-2">
                <Button
                  variant="secondary"
                  className="w-full"
                  onClick={handleCreate}
                  disabled={createExercise.isPending}
                  title={`Add "${query.trim()}" as a new custom exercise`}
                >
                  + Create "{query.trim()}"
                </Button>
              </div>
            )}
          </div>
        )}

        {tab === 'templates' && (
          <div className="flex-1 overflow-y-auto p-2">
            {templatesLoading && <p className="p-4 text-center text-sm text-muted">Loading…</p>}
            {!templatesLoading && templateResults?.items.length === 0 && (
              <p className="p-4 text-center text-sm text-muted">No exercise templates found.</p>
            )}
            {templateResults?.items.map((template) => (
              <button
                key={template.id}
                onClick={() => handleUseTemplate(template)}
                disabled={createExercise.isPending}
                title={`Add "${template.name}" from the exercise template library`}
                className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left hover:bg-border/30 disabled:opacity-50"
              >
                {template.image_url ? (
                  <img
                    src={template.image_url}
                    alt=""
                    className="h-11 w-11 shrink-0 rounded-md bg-border/40 object-cover"
                  />
                ) : (
                  <span className="h-11 w-11 shrink-0 rounded-md bg-border/40" />
                )}
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm capitalize">{template.name}</span>
                  <span className="block truncate text-xs text-muted capitalize">
                    {[template.body_part, template.equipment].filter(Boolean).join(' · ')}
                  </span>
                </span>
              </button>
            ))}
            {templateResults && templateResults.total > templateResults.items.length && (
              <p className="p-2 text-center text-xs text-muted">
                Showing {templateResults.items.length} of {templateResults.total} — refine your search for more.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
        active ? 'border-accent text-accent' : 'border-transparent text-muted'
      }`}
    >
      {children}
    </button>
  )
}

function FilterChip({
  active,
  onClick,
  title,
  children,
}: {
  active: boolean
  onClick: () => void
  title?: string
  children: ReactNode
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`rounded-full px-3 py-1 text-xs font-medium ${
        active ? 'bg-accent text-accent-fg' : 'bg-border/50 text-muted'
      }`}
    >
      {children}
    </button>
  )
}
