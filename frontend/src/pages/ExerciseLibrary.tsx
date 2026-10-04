import { useMemo, useState, type ReactNode } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useGroupMuscles, useInfiniteExerciseTemplates, useMuscleGroups } from '../api/exerciseTemplates'
import { Button, LoadingState, PageTitle } from '../components/ui'
import type { ExerciseTemplate } from '../types'

export function ExerciseLibraryPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [query, setQuery] = useState('')
  // The group and muscle filters live in the URL so other pages can link to a
  // filtered view (e.g. ?group=2&muscle=pectoralis_major).
  const muscleGroupId = Number(searchParams.get('group')) || undefined
  const muscle = searchParams.get('muscle') || undefined
  const { data: groups } = useMuscleGroups()
  const { data: groupMuscles } = useGroupMuscles(muscleGroupId)
  const {
    data,
    isLoading,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteExerciseTemplates({ q: query || undefined, muscleGroupId, muscle })

  const setFilters = (group: number | undefined, muscleSlug: string | undefined) => {
    const next = new URLSearchParams()
    if (group) next.set('group', String(group))
    if (muscleSlug) next.set('muscle', muscleSlug)
    setSearchParams(next)
  }

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
        <FilterChip active={muscleGroupId === undefined} onClick={() => setFilters(undefined, undefined)} title="Show all muscle groups">
          All
        </FilterChip>
        {groups?.map((g) => (
          <FilterChip
            key={g.id}
            active={muscleGroupId === g.id}
            onClick={() => setFilters(g.id, undefined)}
            title={`Filter to ${g.name}`}
            image={g.image_url}
          >
            {g.name}
          </FilterChip>
        ))}
      </div>

      {muscleGroupId !== undefined && groupMuscles && groupMuscles.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <FilterChip active={muscle === undefined} onClick={() => setFilters(muscleGroupId, undefined)} title="Show every muscle in this group">
            All
          </FilterChip>
          {groupMuscles.map((m) => (
            <FilterChip
              key={m.slug}
              active={muscle === m.slug}
              onClick={() => setFilters(muscleGroupId, m.slug)}
              title={`Show exercises that work ${m.name}`}
              image={m.image_url}
            >
              {m.name}
            </FilterChip>
          ))}
        </div>
      )}

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
  image,
  children,
}: {
  active: boolean
  onClick: () => void
  title?: string
  /** Optional small diagram shown before the label. */
  image?: string | null
  children: ReactNode
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`inline-flex items-center gap-1.5 rounded-full py-1 text-xs font-medium ${
        image ? 'pl-1 pr-3' : 'px-3'
      } ${active ? 'bg-accent text-accent-fg' : 'bg-border/50 text-muted'}`}
    >
      {image && (
        <img
          src={image}
          alt=""
          className={`h-5 w-5 shrink-0 rounded-full object-contain ${active ? 'bg-accent-fg/15' : 'bg-surface'}`}
        />
      )}
      {children}
    </button>
  )
}
