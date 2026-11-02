/**
 * A thin blue bar to the left of an exercise card, shown only when it's actually part of a
 * superset -- continuous across every member of the group, including a "giant set" of more
 * than two, so the whole chain reads as one connected block with a visible break only where a
 * superset actually starts or ends. Each member is still its own list row (with its own gap
 * from the next, via the list's own space-y-* spacing), so the bar closes that gap itself with
 * a negative margin on whichever side(s) continue into a neighbor -- `gapPx` must match the
 * list's actual row spacing or the bar will under/overshoot it. Square corners on whichever
 * side(s) continue; a rounded cap only at the true top/bottom of the whole group. Purely a
 * visual indicator: linking/unlinking is a deliberate action in the exercise card's "..." menu
 * (see ExerciseMenu), not something a stray tap on this bar can trigger. Shared by the template
 * editor and the active workout screen so a superset looks the same in both.
 */
export function SupersetBar({
  linkedAbove,
  linkedBelow,
  gapPx,
}: {
  linkedAbove: boolean
  linkedBelow: boolean
  /** The list's own row spacing in pixels (its space-y-* class) -- see ExerciseList. */
  gapPx: number
}) {
  if (!linkedAbove && !linkedBelow) return null
  return (
    <div
      className="w-1.5 shrink-0 bg-accent"
      style={{
        marginTop: linkedAbove ? -gapPx : 0,
        marginBottom: linkedBelow ? -gapPx : 0,
        borderTopLeftRadius: linkedAbove ? 0 : 9999,
        borderTopRightRadius: linkedAbove ? 0 : 9999,
        borderBottomLeftRadius: linkedBelow ? 0 : 9999,
        borderBottomRightRadius: linkedBelow ? 0 : 9999,
      }}
      aria-hidden
    />
  )
}
