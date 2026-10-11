/** Supersets: two adjacent exercises done back to back, sharing a non-null `superset_group`.
 * Mirrors backend/app/services/supersets.py -- a superset is always exactly a pair. */

interface Groupable {
  superset_group: number | null
}

/** True if `a` and `b` are paired -- same non-null group. Either side may be undefined (the
 * exercise before the first one, or after the last one, doesn't exist). */
export function isPaired(a: Groupable | undefined, b: Groupable | undefined): boolean {
  return a?.superset_group != null && a.superset_group === b?.superset_group
}

/**
 * Toggles whether `items[index]` and `items[index + 1]` are paired, mirroring the backend's
 * link/unlink rules exactly (services/supersets.py `link_pair`/`unlink`) -- for local, synchronous
 * use where the whole array gets persisted at once (the template editor; a live workout instead
 * calls useLinkWorkoutExercises / the unlink PATCH directly, since those need to go to the server
 * to allocate a group id and equalize set counts). Returns a new array; `items` itself is
 * untouched.
 */
export function toggleSupersetLink<T extends { superset_group: number | null }>(items: T[], index: number): T[] {
  const a = items[index]
  const b = items[index + 1]
  if (!a || !b) return items

  const next = items.slice()
  if (isPaired(a, b)) {
    next[index] = { ...a, superset_group: null }
    next[index + 1] = { ...b, superset_group: null }
    return next
  }

  // Forming a new pair always breaks whatever either side was previously paired with.
  const oldGroups = new Set([a.superset_group, b.superset_group].filter((g): g is number => g != null))
  const group = Math.max(0, ...items.map((item) => item.superset_group ?? 0)) + 1
  for (let i = 0; i < next.length; i++) {
    if (i === index || i === index + 1) continue
    const g = next[i].superset_group
    if (g != null && oldGroups.has(g)) next[i] = { ...next[i], superset_group: null }
  }
  next[index] = { ...a, superset_group: group }
  next[index + 1] = { ...b, superset_group: group }
  return next
}
