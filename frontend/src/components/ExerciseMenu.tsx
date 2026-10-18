import { useEffect, useRef, useState } from 'react'

export interface ExerciseMenuItem {
  label: string
  title?: string
  onClick: () => void
  danger?: boolean
}

/**
 * The "..." overflow menu in an exercise card's header -- shared by the template editor and the
 * active workout screen so every exercise card's menu looks and behaves the same. Each page
 * supplies whichever items make sense for it (e.g. notes only apply to a live workout; linking a
 * superset applies to both).
 */
export function ExerciseMenu({ items, label = 'More actions' }: { items: ExerciseMenuItem[]; label?: string }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent) {
        if (e.key === 'Escape') setOpen(false)
        return
      }
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', close)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', close)
    }
  }, [open])

  if (items.length === 0) return null

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-muted hover:bg-border/40 ${
          open ? 'bg-border/40' : ''
        }`}
        title={label}
        aria-label={label}
        aria-expanded={open}
      >
        ⋯
      </button>
      {open && (
        <div className="absolute right-0 top-full z-10 mt-1 flex w-52 flex-col overflow-hidden rounded-lg border border-border bg-surface py-1 shadow-lg">
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              onClick={() => {
                setOpen(false)
                item.onClick()
              }}
              title={item.title}
              className={`px-3 py-2 text-left text-sm hover:bg-border/40 ${item.danger ? 'text-danger' : 'text-fg'}`}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
