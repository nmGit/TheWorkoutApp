import type { ReactNode } from 'react'
import type { useDragReorder } from '../hooks/useDragReorder'

type DragReorder = ReturnType<typeof useDragReorder<{ id: number }>>

/** The exercises of a template or a workout, one card each. Pass the drag-reorder state to make
 * the list reorderable. */
export function ExerciseList<T extends { id: number }>({
  items,
  dragReorder,
  renderCard,
  className = 'space-y-3',
}: {
  items: T[]
  dragReorder?: DragReorder
  renderCard: (item: T, index: number) => ReactNode
  className?: string
}) {
  return (
    <div className={className}>
      {items.map((item, index) => (
        <div key={item.id} ref={dragReorder?.getItemRef(item.id)}>
          {renderCard(item, index)}
        </div>
      ))}
    </div>
  )
}
