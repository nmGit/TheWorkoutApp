import type { ReactNode } from 'react'
import { useGroupMuscles, useMuscleGroups } from '../api/exerciseTemplates'

/**
 * The muscle-group / muscle filter chips, shared by every exercise search in the app (the
 * Exercises tab, "Add exercise" in a template, "Add exercise" in an active workout) so they
 * filter the same way and never drift apart. Picking a group shows a second row of that
 * group's own muscles (e.g. Chest -> Pectoralis Major, Serratus Anterior) to narrow further.
 */
export function MuscleGroupFilters({
  muscleGroupId,
  muscle,
  onChange,
}: {
  muscleGroupId: number | undefined
  muscle: string | undefined
  /** Called with the new (group, muscle) pair on any chip tap -- a group change always clears
   * the muscle, since a muscle only makes sense within the group it belongs to. */
  onChange: (muscleGroupId: number | undefined, muscle: string | undefined) => void
}) {
  const { data: groups } = useMuscleGroups()
  const { data: groupMuscles } = useGroupMuscles(muscleGroupId)

  return (
    <>
      <div className="flex flex-wrap gap-1.5">
        <FilterChip active={muscleGroupId === undefined} onClick={() => onChange(undefined, undefined)} title="Show all muscle groups">
          All
        </FilterChip>
        {groups?.map((g) => (
          <FilterChip
            key={g.id}
            active={muscleGroupId === g.id}
            onClick={() => onChange(g.id, undefined)}
            title={`Filter to ${g.name}`}
            image={g.image_url}
          >
            {g.name}
          </FilterChip>
        ))}
      </div>

      {muscleGroupId !== undefined && groupMuscles && groupMuscles.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <FilterChip active={muscle === undefined} onClick={() => onChange(muscleGroupId, undefined)} title="Show every muscle in this group">
            All
          </FilterChip>
          {groupMuscles.map((m) => (
            <FilterChip
              key={m.slug}
              active={muscle === m.slug}
              onClick={() => onChange(muscleGroupId, m.slug)}
              title={`Show exercises that work ${m.name}`}
              image={m.image_url}
            >
              {m.name}
            </FilterChip>
          ))}
        </div>
      )}
    </>
  )
}

export function FilterChip({
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
