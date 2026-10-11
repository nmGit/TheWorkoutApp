import { useEffect, useState } from 'react'
import type { Workout } from '../types'

/** A workout's name, editable inline -- saved on blur, only if it actually changed and isn't
 * blank. Shared by the active workout screen and a completed workout's detail view, so renaming
 * works the same whether the workout is still in progress or long finished. */
export function NameEditor({ workout, onSave }: { workout: Workout; onSave: (name: string) => void }) {
  const [value, setValue] = useState(workout.name)
  useEffect(() => setValue(workout.name), [workout.name])
  return (
    <input
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onBlur={() => value.trim() && value !== workout.name && onSave(value.trim())}
      title="Rename this workout"
      className="-ml-1 w-full min-w-0 rounded px-1 text-xl font-bold focus:bg-border/30 focus:outline-none"
    />
  )
}
