import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { StrengthPoint } from '../types'
import { formatShortDate } from '../lib/format'

/** Strength score over time, as a percentage against your usual (0% = no change). */
export function StrengthChart({ points }: { points: StrengthPoint[] }) {
  const data = points
    .filter((p): p is StrengthPoint & { score: number } => p.score !== null)
    .map((p) => ({
      time: new Date(p.date).getTime(),
      percent: Math.round((p.score - 1) * 1000) / 10,
    }))

  if (data.length < 2) {
    return (
      <div className="flex h-48 items-center justify-center text-center text-sm text-muted">
        Your strength trend appears after a few workouts.
      </div>
    )
  }

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="time"
            type="number"
            domain={['dataMin', 'dataMax']}
            tickFormatter={(t) => formatShortDate(new Date(t).toISOString())}
            tick={{ fontSize: 11, fill: 'var(--color-muted)' }}
            axisLine={{ stroke: 'var(--color-border)' }}
            tickLine={false}
            interval="preserveStartEnd"
            minTickGap={40}
          />
          <YAxis
            tick={{ fontSize: 11, fill: 'var(--color-muted)' }}
            axisLine={false}
            tickLine={false}
            width={44}
            tickFormatter={(v) => `${v > 0 ? '+' : ''}${v}%`}
          />
          <ReferenceLine y={0} stroke="var(--color-muted)" strokeDasharray="4 4" />
          <Tooltip
            formatter={(value) => {
              const v = Number(value)
              return [`${v > 0 ? '+' : ''}${v}%`, 'vs usual']
            }}
            labelFormatter={(label) => formatShortDate(new Date(Number(label)).toISOString())}
            contentStyle={{
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Line
            type="monotone"
            dataKey="percent"
            stroke="var(--color-accent)"
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
