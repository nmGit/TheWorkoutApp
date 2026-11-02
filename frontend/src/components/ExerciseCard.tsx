import type { ReactNode } from 'react'
import { Card } from './ui'

/**
 * The one exercise card. A template's exercises and a workout's exercises are both drawn with it,
 * so they look and behave the same. The parts that differ are passed in: the header's actions,
 * the notes, the rows (planned sets for a template, logged sets for a workout) and the footer.
 *
 * The header is two rows: the title (with its drag handle) on its own, then badges and actions
 * together underneath -- badges on the left, action icons on the right, same as they used to
 * both sit on the title's own row before. Splitting it out keeps a long badge list (or just a
 * long exercise name) from fighting the action icons for space on one line.
 */
export function ExerciseCard({
  title,
  leading,
  badges,
  actions,
  notes,
  footer,
  dragging = false,
  children,
}: {
  title: ReactNode
  /** Drag handle, shown before the title. */
  leading?: ReactNode
  badges?: ReactNode
  /** Buttons at the right of the second row, under the title. */
  actions?: ReactNode
  notes?: ReactNode
  footer?: ReactNode
  dragging?: boolean
  children?: ReactNode
}) {
  return (
    <Card className={dragging ? 'scale-[1.02] shadow-lg' : ''}>
      <div className="mb-1 flex items-center gap-2">
        {leading}
        <h3 className="min-w-0 truncate font-semibold">{title}</h3>
      </div>
      {(badges || actions) && (
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">{badges}</div>
          <div className="flex shrink-0 items-center gap-1">{actions}</div>
        </div>
      )}
      {notes}
      {children}
      {footer}
    </Card>
  )
}
