import { useCallback, useEffect, useRef, useState } from 'react'

const LONG_PRESS_MS = 450
const MOVE_SLOP_PX = 8
const AUTO_SCROLL_EDGE_PX = 72
const AUTO_SCROLL_MAX_SPEED = 16
const SETTLE_MS = 180
const SETTLE_TRANSITION = `transform ${SETTLE_MS}ms ease`

type Key = string | number

interface DragState {
  key: Key
  pointerId: number
  startClientY: number
  startScrollY: number
  lastClientY: number
  originalIndex: number
  targetIndex: number
  draggedHeight: number
  gap: number
  // Captured once at drag start; never re-measured mid-gesture, since
  // `transform` (used for both the dragged item and the "bump" shift of
  // its siblings) doesn't affect layout, so re-measuring would just read
  // back the same untransformed boxes anyway. Auto-scroll during the drag
  // is handled separately by tracking how far the page has scrolled since
  // `startScrollY`, not by re-measuring these.
  originalCenters: { key: Key; center: number }[]
}

/**
 * Press-and-hold-then-drag reordering for a list of items, driven entirely
 * by native Pointer Events (no library). Mid-drag, nothing touches React
 * state -- every visual update is a direct `transform: translateY(...)`
 * write to the relevant DOM node via ref, throttled to one per animation
 * frame. React state changes exactly twice per gesture: once when the
 * long-press activates (for `isDragging`, so callers can style the active
 * handle/card) and once on commit, when the caller's `onReorderCommit`
 * fires with the final order -- the actual reordering of `items` is the
 * caller's responsibility (e.g. an optimistic mutation), not this hook's.
 *
 * The target slot during a drag is found by comparing the dragged item's
 * live center against every sibling's ORIGINAL (drag-start) center: the
 * target index is just how many siblings have a smaller original center.
 * This is deliberately simpler than cumulative height/offset math, and it
 * stays correct even though list items (exercise cards) can have very
 * different heights depending on how many sets they hold.
 *
 * Also auto-scrolls the page when the pointer nears the top/bottom edge of
 * the viewport while dragging, so reordering across a long list doesn't
 * require dropping, scrolling manually, and starting a new drag for every
 * step -- see `autoScrollTick` for the scroll-compensation math this needs.
 */
export function useDragReorder<T>(
  items: T[],
  getKey: (item: T) => Key,
  onReorderCommit: (newOrder: T[]) => void,
) {
  const itemsRef = useRef(items)
  useEffect(() => {
    itemsRef.current = items
  }, [items])

  const nodeRefs = useRef(new Map<Key, HTMLElement>())
  const dragRef = useRef<DragState | null>(null)
  const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pointerDownAt = useRef<{ x: number; y: number; pointerId: number } | null>(null)
  const rafPending = useRef(false)

  const [draggingKey, setDraggingKey] = useState<Key | null>(null)

  const clearLongPressTimer = () => {
    if (longPressTimer.current !== null) {
      clearTimeout(longPressTimer.current)
      longPressTimer.current = null
    }
  }

  // `transition: none` matters here, not just the transform reset -- by the
  // time this runs, every node already carries the settle transition (set
  // in `startDrag`/`endDrag`), and calling this right as the reorder swaps
  // DOM order relies on the clear itself being instantaneous rather than
  // animating a second time back to 0.
  const resetTransforms = () => {
    for (const node of nodeRefs.current.values()) {
      node.style.transition = 'none'
      node.style.transform = ''
    }
  }

  // Applies the current drag position to the dragged node, and shifts any
  // sibling the drag has moved past out of the way. `targetIndex` is
  // recomputed from `originalCenters` each call, so this is the single
  // place that decides both the dragged item's translate and every
  // sibling's bump.
  //
  // If the page has auto-scrolled since the drag started, a plain
  // `translateY(dy)` would let the dragged item visually drift away from
  // the pointer: its untransformed (in-flow) position already moves with
  // page scroll like any element, so without correction the transform and
  // the scroll would stack. Adding `scrollDelta` to the transform cancels
  // that out, keeping the item pinned to the pointer regardless of how
  // much the page has scrolled underneath it. The target-index comparison
  // needs the opposite adjustment: siblings' cached positions are in
  // "scroll started here" coordinates, so `scrollDelta` has to be added to
  // the dragged item's comparison value (not its transform) to compare
  // apples to apples -- this is also what makes items scroll *into* range
  // as auto-scroll proceeds, rather than only ever comparing against
  // whatever was on screen at drag-start.
  const applyFrame = (drag: DragState, dy: number) => {
    const scrollDelta = window.scrollY - drag.startScrollY

    const draggedNode = nodeRefs.current.get(drag.key)
    if (draggedNode) draggedNode.style.transform = `translateY(${dy + scrollDelta}px)`

    const draggedOriginal = drag.originalCenters.find((c) => c.key === drag.key)?.center ?? 0
    const draggedComparisonCenter = draggedOriginal + dy + scrollDelta
    let targetIndex = 0
    for (const c of drag.originalCenters) {
      if (c.key === drag.key) continue
      if (c.center < draggedComparisonCenter) targetIndex++
    }
    drag.targetIndex = targetIndex

    const shift = drag.draggedHeight + drag.gap
    for (const [siblingOriginalIndex, c] of drag.originalCenters.entries()) {
      if (c.key === drag.key) continue
      const node = nodeRefs.current.get(c.key)
      if (!node) continue
      let siblingShift = 0
      if (siblingOriginalIndex > drag.originalIndex && siblingOriginalIndex <= targetIndex) {
        siblingShift = -shift
      } else if (siblingOriginalIndex < drag.originalIndex && siblingOriginalIndex >= targetIndex) {
        siblingShift = shift
      }
      node.style.transform = siblingShift ? `translateY(${siblingShift}px)` : ''
    }
  }

  // Runs every frame for the duration of a drag (self-terminates once
  // `dragRef.current` is cleared). Scrolls the page when the pointer is
  // near the top/bottom edge of the viewport -- without this, reordering
  // across a long list means dropping, manually scrolling, and starting a
  // new drag for each step. Only calls `applyFrame` when actually
  // scrolling; otherwise there's nothing new to recompute this frame.
  const autoScrollTick = () => {
    const drag = dragRef.current
    if (!drag) return

    const viewportHeight = window.innerHeight
    const y = drag.lastClientY
    let speed = 0
    if (y < AUTO_SCROLL_EDGE_PX) {
      speed = -AUTO_SCROLL_MAX_SPEED * (1 - y / AUTO_SCROLL_EDGE_PX)
    } else if (y > viewportHeight - AUTO_SCROLL_EDGE_PX) {
      speed = AUTO_SCROLL_MAX_SPEED * (1 - (viewportHeight - y) / AUTO_SCROLL_EDGE_PX)
    }
    if (speed !== 0) {
      window.scrollBy(0, speed)
      applyFrame(drag, drag.lastClientY - drag.startClientY)
    }
    requestAnimationFrame(autoScrollTick)
  }

  // Settling happens in two steps, not one: first animate the dragged node
  // to the exact spot it'll end up at (computed the same way sibling bumps
  // are), *then* -- only after that transition has had time to finish --
  // swap the underlying array order and clear transforms. Swapping order
  // immediately would jump the item straight to its rest position instead
  // of visibly sliding there; deferring it is what makes the swap itself
  // invisible. Safe against overlapping with a fresh drag: starting a new
  // one requires another full LONG_PRESS_MS (450ms) of holding, well after
  // this SETTLE_MS (180ms) callback has already run.
  const endDrag = useCallback(
    (commit: boolean) => {
      const drag = dragRef.current
      dragRef.current = null
      if (!drag) {
        setDraggingKey(null)
        resetTransforms()
        return
      }

      const shouldReorder = commit && drag.targetIndex !== drag.originalIndex
      const current = itemsRef.current
      const keys = current.map(getKey)
      const fromIdx = keys.indexOf(drag.key)
      // item vanished mid-drag (e.g. removed, or a refetch swapped ids) -- abort quietly
      const canCommit = shouldReorder && fromIdx !== -1

      const shift = drag.draggedHeight + drag.gap
      const finalOffset = canCommit ? (drag.targetIndex - drag.originalIndex) * shift : 0
      const draggedNode = nodeRefs.current.get(drag.key)
      if (draggedNode) {
        draggedNode.style.transition = SETTLE_TRANSITION
        draggedNode.style.transform = finalOffset ? `translateY(${finalOffset}px)` : ''
      }

      window.setTimeout(() => {
        setDraggingKey(null)
        resetTransforms()
        if (canCommit) {
          const reordered = [...current]
          const [moved] = reordered.splice(fromIdx, 1)
          const toIdx = Math.min(drag.targetIndex, reordered.length)
          reordered.splice(toIdx, 0, moved)
          onReorderCommit(reordered)
        }
      }, SETTLE_MS)
    },
    [getKey, onReorderCommit],
  )

  const onPointerMove = useCallback(
    (e: PointerEvent) => {
      const drag = dragRef.current
      if (!drag || e.pointerId !== drag.pointerId) return

      const stillExists = itemsRef.current.some((it) => getKey(it) === drag.key)
      if (!stillExists) {
        endDrag(false)
        return
      }

      drag.lastClientY = e.clientY
      const dy = e.clientY - drag.startClientY
      if (!rafPending.current) {
        rafPending.current = true
        requestAnimationFrame(() => {
          rafPending.current = false
          if (dragRef.current === drag) applyFrame(drag, dy)
        })
      }
    },
    [getKey, endDrag],
  )

  const onPointerUp = useCallback(
    (e: PointerEvent) => {
      if (dragRef.current?.pointerId === e.pointerId) endDrag(true)
      pointerDownAt.current = null
      clearLongPressTimer()
    },
    [endDrag],
  )

  const onPointerCancel = useCallback(
    (e: PointerEvent) => {
      if (dragRef.current?.pointerId === e.pointerId) endDrag(false)
      pointerDownAt.current = null
      clearLongPressTimer()
    },
    [endDrag],
  )

  useEffect(() => {
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerup', onPointerUp)
    window.addEventListener('pointercancel', onPointerCancel)
    return () => {
      window.removeEventListener('pointermove', onPointerMove)
      window.removeEventListener('pointerup', onPointerUp)
      window.removeEventListener('pointercancel', onPointerCancel)
      clearLongPressTimer()
    }
  }, [onPointerMove, onPointerUp, onPointerCancel])

  const startDrag = (key: Key, e: React.PointerEvent) => {
    const order = itemsRef.current.map(getKey)
    const originalIndex = order.indexOf(key)
    if (originalIndex === -1) return

    const originalCenters = order
      .map((k) => {
        const node = nodeRefs.current.get(k)
        if (!node) return null
        const r = node.getBoundingClientRect()
        return { key: k, center: r.top + r.height / 2, top: r.top, height: r.height }
      })
      .filter((c): c is NonNullable<typeof c> => c !== null)

    const draggedRect = originalCenters.find((c) => c.key === key)
    if (!draggedRect) return
    // `originalCenters` is already in top-to-bottom render order (it's
    // built from `items`, and items render via a plain in-order `.map()`
    // with no reordering CSS involved) -- gap is just the space between
    // any two adjacent entries, no separate sort needed.
    const gap =
      originalCenters.length > 1
        ? Math.max(0, originalCenters[1].top - (originalCenters[0].top + originalCenters[0].height))
        : 0

    dragRef.current = {
      key,
      pointerId: e.pointerId,
      startClientY: e.clientY,
      startScrollY: window.scrollY,
      lastClientY: e.clientY,
      originalIndex,
      targetIndex: originalIndex,
      draggedHeight: draggedRect.height,
      gap,
      originalCenters: originalCenters.map((c) => ({ key: c.key, center: c.center })),
    }
    setDraggingKey(key)
    // Siblings get the settle transition for their whole bump lifecycle, so
    // each shift as the drag crosses a new sibling's center slides instead
    // of snapping. The dragged node stays untransitioned so it tracks the
    // pointer with zero lag; `endDrag` turns its transition on only for the
    // final settle move.
    for (const [k, node] of nodeRefs.current.entries()) {
      node.style.transition = k === key ? '' : SETTLE_TRANSITION
    }
    try {
      ;(e.target as Element).setPointerCapture(e.pointerId)
    } catch {
      // Untrusted/synthetic events (tests) throw here -- harmless to skip.
    }
    requestAnimationFrame(autoScrollTick)
  }

  const getHandleProps = (key: Key) => ({
    onPointerDown: (e: React.PointerEvent) => {
      if (e.pointerType === 'mouse' && e.button !== 0) return
      pointerDownAt.current = { x: e.clientX, y: e.clientY, pointerId: e.pointerId }
      clearLongPressTimer()
      longPressTimer.current = setTimeout(() => {
        longPressTimer.current = null
        if (pointerDownAt.current?.pointerId === e.pointerId) startDrag(key, e)
      }, LONG_PRESS_MS)
    },
    onPointerMove: (e: React.PointerEvent) => {
      const down = pointerDownAt.current
      if (!down || down.pointerId !== e.pointerId || dragRef.current) return
      const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y)
      if (moved > MOVE_SLOP_PX) {
        clearLongPressTimer()
        pointerDownAt.current = null
      }
    },
    onContextMenu: (e: React.MouseEvent) => e.preventDefault(),
    style: {
      touchAction: 'none',
      userSelect: 'none',
      WebkitUserSelect: 'none',
      WebkitTouchCallout: 'none',
    } as React.CSSProperties,
    'data-drag-handle': true,
  })

  const getItemRef = useCallback(
    (key: Key) => (el: HTMLElement | null) => {
      if (el) nodeRefs.current.set(key, el)
      else nodeRefs.current.delete(key)
    },
    [],
  )

  return {
    getHandleProps,
    getItemRef,
    isBeingDragged: (key: Key) => draggingKey === key,
  }
}
