/** Supersets: two or more adjacent exercises done back to back, sharing a non-null
 * `superset_group` -- a contiguous run of any size ("giant sets" when there are more than
 * two). Mirrors backend/app/services/supersets.py. */

interface Groupable {
  superset_group: number | null
}

/** True if `a` and `b` are paired -- same non-null group. Either side may be undefined (the
 * exercise before the first one, or after the last one, doesn't exist). */
export function isPaired(a: Groupable | undefined, b: Groupable | undefined): boolean {
  return a?.superset_group != null && a.superset_group === b?.superset_group
}

/** Mirrors backend services/supersets.py normalize_superset_groups: clears `superset_group` on
 * any contiguous run (in array order) shorter than two members -- a lone exercise is never "a
 * superset" by itself. `items` must already be in position order. Returns a new array. */
export function normalizeSupersetGroups<T extends { superset_group: number | null }>(items: T[]): T[] {
  const next = items.slice()
  let i = 0
  while (i < next.length) {
    const group = next[i].superset_group
    if (group === null) {
      i += 1
      continue
    }
    let j = i
    while (j + 1 < next.length && next[j + 1].superset_group === group) j += 1
    if (j === i) next[i] = { ...next[i], superset_group: null }
    i = j + 1
  }
  return next
}

/**
 * Toggles whether `items[index]` and `items[index + 1]` are paired, mirroring the backend's
 * link/unlink rules exactly (services/supersets.py `link_pair`/`unlink`) -- for local, synchronous
 * use where the whole array gets persisted at once (the template editor; a live workout instead
 * calls useLinkWorkoutExercises / the unlink PATCH directly, since those need to go to the server
 * to allocate a group id and equalize set counts). Returns a new array; `items` itself is
 * untouched.
 *
 * Already paired: removes just `items[index]` from the superset (same as the backend's `unlink`
 * on one item), leaving the rest of any chain on either side intact, then normalizes in case that
 * left either side down to a single member.
 *
 * Not yet paired: joins whichever existing chain(s) either side already belongs to -- extending
 * a chain, or merging two chains into one -- rather than always starting a fresh, disconnected
 * pair, so repeating this across a run of adjacent exercises builds one growing "giant set".
 */
export function toggleSupersetLink<T extends { superset_group: number | null }>(items: T[], index: number): T[] {
  const a = items[index]
  const b = items[index + 1]
  if (!a || !b) return items

  const next = items.slice()
  if (isPaired(a, b)) {
    next[index] = { ...a, superset_group: null }
    return normalizeSupersetGroups(next)
  }

  const group = a.superset_group ?? b.superset_group ?? Math.max(0, ...items.map((item) => item.superset_group ?? 0)) + 1
  const oldGroups = new Set([a.superset_group, b.superset_group].filter((g): g is number => g != null && g !== group))
  for (let i = 0; i < next.length; i++) {
    if (oldGroups.has(next[i].superset_group as number)) next[i] = { ...next[i], superset_group: group }
  }
  next[index] = { ...a, superset_group: group }
  next[index + 1] = { ...b, superset_group: group }
  return next
}
