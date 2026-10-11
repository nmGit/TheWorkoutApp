/** Whether progressive overload moved a field up or down from what it was last time -- shared
 * between the active workout screen's ghost text (SetRow) and the template editor's preview of
 * what progression *would* do (PlanSets), so both color the same way. */
export type Tone = 'up' | 'down' | null

/** Up if `planned` is more than `previous`, down if less, otherwise no tone (including when
 * either value is unknown -- a plain copy, same as last time, is never colored). */
export function tone(planned: number | null, previous: number | null): Tone {
  if (planned === null || previous === null) return null
  if (planned > previous) return 'up'
  if (planned < previous) return 'down'
  return null
}

/** The ghost text's color as a `placeholder:` modifier, for an <input>: muted green when
 * progressive overload raised this field over last time, muted amber when it lowered it, the
 * ordinary muted grey otherwise. */
export function tonePlaceholderClass(t: Tone): string {
  if (t === 'up') return 'placeholder:text-success/70'
  if (t === 'down') return 'placeholder:text-amber-600/70'
  return 'placeholder:text-muted'
}

/** Same coloring as tonePlaceholderClass, as a plain text color -- for ghost text that isn't an
 * input placeholder (e.g. the template editor's read-only preview). */
export function toneTextClass(t: Tone): string {
  if (t === 'up') return 'text-success/70'
  if (t === 'down') return 'text-amber-600/70'
  return 'text-muted/60'
}
