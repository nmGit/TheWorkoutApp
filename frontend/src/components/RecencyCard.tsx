import { useMemo } from 'react'
import { useMuscleRecency } from '../api/recency'
import { recencyFills } from '../lib/recency'
import { MuscleMapPair } from './MuscleMap'
import { Card } from './ui'

/** The body diagram coloured by how recently each muscle was worked: green up to 2 days, fading
 * to red by 8 days, red after that, grey if never worked. */
export function RecencyCard() {
  const { data } = useMuscleRecency()
  const fills = useMemo(() => recencyFills(data?.muscles), [data])
  return (
    <Card className="space-y-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full" style={{ background: 'rgb(22, 163, 74)' }} /> 2 days or less
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full" style={{ background: 'linear-gradient(to right, hsl(142, 80%, 37%), hsl(60, 80%, 46%), hsl(0, 80%, 50%))' }} /> 2–8 days, fading
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full" style={{ background: 'rgb(220, 38, 38)' }} /> 8 days or more
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full" style={{ background: '#6b7280' }} /> never
        </span>
      </div>
      <MuscleMapPair primary={[]} secondary={[]} fills={fills} showLabels interactive={false} className="h-56 w-full" />
    </Card>
  )
}
