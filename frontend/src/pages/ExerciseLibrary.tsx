import { useMemo, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useInfiniteExerciseTemplates, useMuscleGroups } from '../api/exerciseTemplates'
import { Button, LoadingState, PageTitle } from '../components/ui'
import type { ExerciseTemplate } from '../types'

export function ExerciseLibraryPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [muscleGroupId, setMuscleGroupId] = useState<number | undefined>(undefined)
  const { data: groups } = useMuscleGroups()
  const {
    data,
    isLoading,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteExerciseTemplates({ q: query || undefined, muscleGroupId })

  const items = useMemo(() => data?.pages.flatMap((p) => p.items) ?? [], [data])
  const total = data?.pages[0]?.total ?? 0

  const grouped = useMemo(() => {
    const map = new Map<string, ExerciseTemplate[]>()
    for (const t of items) {
      const key = t.muscle_group_name ?? 'Other'
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(t)
    }
    const order = new Map((groups ?? []).map((g) => [g.name, g.display_order]))
    return new Map([...map.entries()].sort((a, b) => (order.get(a[0]) ?? 99) - (order.get(b[0]) ?? 99)))
  }, [items, groups])

  const handleSelect = (template: ExerciseTemplate) => {
    navigate(`/exercises/${template.id}`)
  }

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
            {items.map((t) => (
              <button
                key={t.id}
                onClick={() => handleSelect(t)}
                title={`View ${t.name}'s exercise page`}
                className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-border/20"
              >
                <span className="flex min-w-0 items-center gap-3">
                  {t.image_url ? (
                    <img src={t.image_url} alt="" className="h-8 w-8 shrink-0 rounded-md bg-border/40 object-cover" />
                  ) : (
                    <span className="h-8 w-8 shrink-0 rounded-md bg-border/40" />
                  )}
                  <span className="min-w-0">
                    <span className="block truncate text-sm capitalize">{t.name}</span>
                    <span className="block truncate text-xs text-muted capitalize">
                      {[t.muscle_group_name, t.equipment].filter(Boolean).join(' · ')}
                    </span>
                  </span>
                </span>
              </button>
            ))}
          </div>
        </div>
      ))}

      {hasNextPage && (
        <Button
          variant="secondary"
          className="w-full"
          onClick={() => fetchNextPage()}
          disabled={isFetchingNextPage}
        >
          {isFetchingNextPage ? 'Loading…' : `Load more (${items.length} of ${total})`}
        </Button>
      )}
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
