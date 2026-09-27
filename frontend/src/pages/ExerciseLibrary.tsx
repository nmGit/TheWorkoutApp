import { useMemo, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useExercises, useMuscleGroups } from '../api/exercises'
import { LoadingState, PageTitle } from '../components/ui'
import type { Exercise } from '../types'

export function ExerciseLibraryPage() {
  const [query, setQuery] = useState('')
  const [muscleGroupId, setMuscleGroupId] = useState<number | undefined>(undefined)
  const { data: groups } = useMuscleGroups()
  const { data: exercises, isLoading } = useExercises({ q: query || undefined, muscleGroupId })

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

  return (
    <div className="space-y-4">
      <PageTitle>Exercises</PageTitle>

      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search exercises…"
        className="h-11 w-full rounded-lg border border-border bg-surface px-3 text-sm"
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

      {isLoading && <LoadingState />}

      {[...grouped.entries()].map(([group, items]) => (
        <div key={group}>
          <p className="mb-1 px-1 text-xs font-semibold uppercase text-muted">{group}</p>
          <div className="divide-y divide-border rounded-xl border border-border bg-surface">
            {items.map((ex) => (
              <Link
                key={ex.id}
                to={`/exercises/${ex.id}`}
                title={`View ${ex.name}'s exercise page`}
                className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-border/20"
              >
                <span className="flex min-w-0 items-center gap-3">
                  {ex.template?.image_url ? (
                    <img
                      src={ex.template.image_url}
                      alt=""
                      className="h-8 w-8 shrink-0 rounded-md bg-border/40 object-cover"
                    />
                  ) : null}
                  <span className="truncate text-sm">{ex.name}</span>
                </span>
                {ex.last_performed && <span className="shrink-0 text-xs text-muted">{ex.last_performed.summary}</span>}
              </Link>
            ))}
          </div>
        </div>
      ))}
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
