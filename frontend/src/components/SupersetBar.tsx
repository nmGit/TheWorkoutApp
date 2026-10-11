/**
 * A thin blue bar to the left of an exercise card, shown only when it's actually part of a
 * superset -- continuous across both paired cards, so a linked pair reads as one connected
 * block. Purely a visual indicator: linking/unlinking is a deliberate action in the exercise
 * card's "..." menu (see ExerciseMenu), not something a stray tap on this bar can trigger.
 * Shared by the template editor and the active workout screen so a superset looks the same in
 * both.
 */
export function SupersetBar({ linkedAbove, linkedBelow }: { linkedAbove: boolean; linkedBelow: boolean }) {
  if (!linkedAbove && !linkedBelow) return null
  return <div className="w-1.5 shrink-0 rounded-full bg-accent" aria-hidden />
}
