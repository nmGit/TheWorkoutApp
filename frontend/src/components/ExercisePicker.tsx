import { useMemo, useState, type ReactNode } from 'react'
import { useCreateExerciseTemplate, useExerciseTemplates, useMuscleGroups } from '../api/exerciseTemplates'
import type { ExerciseTemplate } from '../types'
import { Button } from './ui'

interface Props {
  onSelect: (exercise: ExerciseTemplate) => void
  onClose: () => void
}

export function ExercisePicker({ onSelect, onClose }: Props) {
  const [query, setQuery] = useState('')
  const [muscleGroupId, setMuscleGroupId] = useState<number | undefined>(undefined)
  const { data: groups } = useMuscleGroups()
  const { data: results, isLoading } = useExerciseTemplates({
    q: query || undefined,
    muscleGroupId,
    limit: 40,
  })
  const createExercise = useCreateExerciseTemplate()

  const grouped = useMemo(() => {
    const map = new Map<string, ExerciseTemplate[]>()
    for (const ex of results?.items ?? []) {
      const key = ex.muscle_group_name ?? 'Other'
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(ex)
    }
    const order = new Map((groups ?? []).map((g) => [g.name, g.display_order]))
    return new Map([...map.entries()].sort((a, b) => (order.get(a[0]) ?? 99) - (order.get(b[0]) ?? 99)))
  }, [results, groups])

  const canCreate =
    query.trim().length > 0 && results?.items.every((e) => e.name.toLowerCase() !== query.trim().toLowerCase())

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

        <div className="space-y-2 border-b border-border p-4">
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search exercises…"
            className="h-11 w-full rounded-lg border border-border bg-bg px-3 text-sm"
          />
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
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {isLoading && <p className="p-4 text-center text-sm text-muted">Loading…</p>}
          {!isLoading && results?.items.length === 0 && !canCreate && (
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
                  className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left hover:bg-border/30"
                >
                  {ex.image_url ? (
                    <img src={ex.image_url} alt="" className="h-10 w-10 shrink-0 rounded-md bg-border/40 object-cover" />
                  ) : (
                    <span className="h-10 w-10 shrink-0 rounded-md bg-border/40" />
                  )}
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm capitalize">{ex.name}</span>
                    {ex.equipment && (
                      <span className="block truncate text-xs text-muted capitalize">{ex.equipment}</span>
                    )}
                  </span>
                  {ex.last_performed && <span className="text-xs text-muted">{ex.last_performed.summary}</span>}
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

          {results && results.total > results.items.length && (
            <p className="p-2 text-center text-xs text-muted">
              Showing {results.items.length} of {results.total} — refine your search for more.
            </p>
          )}
        </div>
      </div>
    </div>
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
