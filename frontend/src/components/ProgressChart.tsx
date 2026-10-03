import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { StatsPoint } from '../types'
import { formatShortDate } from '../lib/format'

export function ProgressChart({ series, unit }: { series: StatsPoint[]; unit: string }) {
  if (series.length < 2) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted">
        Log this exercise a couple more times to see a trend.
      </div>
    )
  }

  // Recharts' XAxis defaults to a "category" scale, which places points at
  // equal steps by index and ignores the actual value -- since `date` is a
  // string, that silently discarded the real time gaps between workouts.
  // Converting to a numeric timestamp and setting `type="number"` switches
  // it to a true linear/time scale.
  const data = series.map((p) => ({ ...p, time: new Date(p.date).getTime() }))

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
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
          />
          <Tooltip
            formatter={(value) => [`${value} ${unit}`, undefined]}
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
            dataKey="value"
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
