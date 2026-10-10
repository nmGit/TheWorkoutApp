import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useGenerateGroups, useGenerateWorkout } from '../api/generate'
import { Button } from './ui'

/** A button that opens a small panel: how many strength exercises, and whether to add a
 * stretch and a cardio exercise. The workout favours the muscles trained least recently. */
export function GenerateWorkout() {
  const navigate = useNavigate()
  const generate = useGenerateWorkout()
  const [open, setOpen] = useState(false)
  // The field's text is kept as typed, so it can be cleared and retyped. It's checked on blur.
  const [countText, setCountText] = useState('4')
  const count = Math.min(10, Math.max(1, Math.round(Number(countText) || 1)))
  const [stretching, setStretching] = useState(false)
  const [cardio, setCardio] = useState(false)
  const [familiarFirst, setFamiliarFirst] = useState(true)
  const { data: ranking } = useGenerateGroups(open)
  // The groups to work. The two most in need are selected by default, once the ranking arrives.
  const [selected, setSelected] = useState<string[] | null>(null)
  useEffect(() => {
    if (ranking && selected === null) setSelected(ranking.slice(0, 2).map((g) => g.name))
  }, [ranking, selected])

  const submit = async () => {
    setCountText(String(count))
    // In the order of need, so the first chosen group is the most overdue.
    const groups = (ranking ?? []).map((g) => g.name).filter((name) => selected?.includes(name))
    await generate.mutateAsync({ count, stretching, cardio, familiarFirst, groups })
    navigate('/workout/active')
  }

  if (!open) {
    return (
      <Button variant="secondary" className="w-full" onClick={() => setOpen(true)} title="Build a workout from the muscles you've trained least recently">
        Generate Workout
      </Button>
    )
  }

  const toggle = (on: boolean, set: (v: boolean) => void, label: string) => (
    <button
      type="button"
      onClick={() => set(!on)}
      aria-pressed={on}
      className={`h-9 rounded-full px-3 text-sm font-medium ${on ? 'bg-accent text-accent-fg' : 'bg-border/60 text-fg'}`}
    >
      {label}
    </button>
  )

  return (
    <div className="space-y-3 rounded-lg border border-border p-3">
      <label className="flex items-center justify-between gap-3 text-sm">
        <span>Strength exercises</span>
        <input
          type="number"
          min={1}
          max={10}
          value={countText}
          onChange={(e) => setCountText(e.target.value)}
          onBlur={() => setCountText(String(count))}
          className="h-10 w-20 rounded-md border border-border bg-bg px-2 text-center tabular-nums"
        />
      </label>
      <div className="flex flex-wrap gap-2">
        {toggle(stretching, setStretching, 'Add stretching')}
        {toggle(cardio, setCardio, 'Add cardio')}
      </div>
      <div className="flex flex-wrap gap-2">
        {toggle(familiarFirst, setFamiliarFirst, 'Prioritize familiar exercises')}
      </div>
      <div className="space-y-1.5">
        <p className="text-xs text-muted">Groups, most in need first</p>
        <div className="flex flex-wrap gap-2">
          {(ranking ?? []).map((g) => {
            const on = selected?.includes(g.name) ?? false
            return (
              <button
                key={g.name}
                type="button"
                aria-pressed={on}
                onClick={() =>
                  setSelected((prev) => {
                    const current = prev ?? []
                    return on ? current.filter((n) => n !== g.name) : [...current, g.name]
                  })
                }
                className={`h-9 rounded-full px-3 text-sm font-medium ${on ? 'bg-accent text-accent-fg' : 'bg-border/60 text-fg'}`}
              >
                {g.name}
                {g.trained > 0 && (
                  <span className="ml-1.5 text-xs opacity-70">
                    {g.in_need}/{g.trained}
                  </span>
                )}
              </button>
            )
          })}
        </div>
      </div>
      {generate.error && <p className="text-sm text-danger">{generate.error.message}</p>}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
        <Button onClick={submit} disabled={generate.isPending || !selected?.length}>
          {generate.isPending ? 'Building…' : 'Generate'}
        </Button>
      </div>
    </div>
  )
}
