import { createContext, useContext, useRef, useState, type ReactNode } from 'react'

/** How long a deletion can be undone before it's sent to the server. */
const UNDO_WINDOW_MS = 5000

interface Pending {
  id: number
  message: string
  /** Key of the item hidden from its list while the deletion is pending. */
  hideKey?: string
  /** Sends the deletion to the server once the undo window closes. */
  commit?: () => Promise<unknown>
  /** Reverts a change that was already made. */
  onUndo?: () => void
}

interface UndoApi {
  /** Hides the item right away and deletes it on the server after the undo window. */
  deleteWithUndo: (options: { message: string; hideKey: string; commit: () => Promise<unknown> }) => void
  /** Offers undo for a change that has already been saved. */
  showUndo: (options: { message: string; onUndo: () => void }) => void
  /** True while an item is hidden because its deletion is still pending. */
  isHidden: (hideKey: string) => boolean
}

const UndoContext = createContext<UndoApi | null>(null)

export function UndoProvider({ children }: { children: ReactNode }) {
  const [shown, setShown] = useState<Pending | null>(null)
  const [hidden, setHidden] = useState<ReadonlySet<string>>(() => new Set())
  // Timers and the closures they run aren't kept in state: they must not re-render, and
  // a timer must still fire after the page that started it has unmounted.
  const timers = useRef(new Map<number, number>())
  const nextId = useRef(1)
  const pending = useRef(new Map<number, Pending>())

  const setHiddenKey = (key: string, isHidden: boolean) =>
    setHidden((prev) => {
      const next = new Set(prev)
      if (isHidden) next.add(key)
      else next.delete(key)
      return next
    })

  const schedule = (entry: Pending) => {
    pending.current.set(entry.id, entry)
    if (entry.hideKey) setHiddenKey(entry.hideKey, true)
    setShown(entry)
    const timer = window.setTimeout(() => finish(entry.id), UNDO_WINDOW_MS)
    timers.current.set(entry.id, timer)
  }

  const finish = async (id: number) => {
    const entry = pending.current.get(id)
    timers.current.delete(id)
    pending.current.delete(id)
    setShown((current) => (current?.id === id ? null : current))
    if (!entry?.commit) return
    try {
      await entry.commit()
    } catch {
      // The server refused the delete: the item is still there, so show it again.
      setShown({ id: -id, message: `Couldn't delete: ${entry.message}` })
      window.setTimeout(() => setShown((c) => (c?.id === -id ? null : c)), UNDO_WINDOW_MS)
    } finally {
      if (entry.hideKey) setHiddenKey(entry.hideKey, false)
    }
  }

  const undo = (entry: Pending) => {
    window.clearTimeout(timers.current.get(entry.id))
    timers.current.delete(entry.id)
    pending.current.delete(entry.id)
    if (entry.hideKey) setHiddenKey(entry.hideKey, false)
    entry.onUndo?.()
    setShown((current) => (current?.id === entry.id ? null : current))
  }

  const api: UndoApi = {
    deleteWithUndo: ({ message, hideKey, commit }) =>
      schedule({ id: nextId.current++, message, hideKey, commit }),
    showUndo: ({ message, onUndo }) => schedule({ id: nextId.current++, message, onUndo }),
    isHidden: (hideKey) => hidden.has(hideKey),
  }

  return (
    <UndoContext.Provider value={api}>
      {children}
      {shown && (
        <div
          role="status"
          aria-live="polite"
          className="fixed inset-x-0 bottom-20 z-50 mx-auto flex w-[calc(100%-2rem)] max-w-md items-center justify-between gap-3 rounded-xl border border-border bg-surface px-4 py-3 text-sm text-fg shadow-lg"
        >
          <span className="min-w-0 truncate">{shown.message}</span>
          {(shown.commit || shown.onUndo) && (
            <button
              onClick={() => undo(shown)}
              title="Undo this change"
              className="shrink-0 font-semibold text-accent hover:underline"
            >
              Undo
            </button>
          )}
        </div>
      )}
    </UndoContext.Provider>
  )
}

export function useUndo(): UndoApi {
  const ctx = useContext(UndoContext)
  if (!ctx) throw new Error('useUndo must be used inside <UndoProvider>')
  return ctx
}
