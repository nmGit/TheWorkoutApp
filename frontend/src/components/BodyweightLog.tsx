import { useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useBodyweightEntries, useDeleteBodyweight, useUpsertBodyweight } from '../api/settings'
import { useAppSettings } from '../context/SettingsContext'
import { useUndo } from '../context/UndoContext'
import { formatDate, formatShortDate, formatWeight } from '../lib/format'
import { convertWeight } from '../lib/units'
import { Button, Card } from './ui'

/** Logging and a trend chart for body weight: a date is unique, so logging again on the same
 * day replaces that day's entry rather than adding another point. */
export function BodyweightLog() {
  const settings = useAppSettings()
  const { data: bodyweight } = useBodyweightEntries()
  const upsertBodyweight = useUpsertBodyweight()
  const deleteBodyweight = useDeleteBodyweight()
  const { deleteWithUndo, isHidden } = useUndo()
  const [newWeight, setNewWeight] = useState('')
  const [logError, setLogError] = useState<string | null>(null)

  const handleLogWeight = async () => {
    if (!newWeight) return
    setLogError(null)
    try {
      await upsertBodyweight.mutateAsync({ weight: Number(newWeight) })
      // Only clear the field once the entry is actually saved -- clearing it unconditionally
      // made a failed save look like it worked, with nothing logged and no sign anything was wrong.
      setNewWeight('')
    } catch (err) {
      setLogError(err instanceof Error ? err.message : "Couldn't log that weight.")
    }
  }

  // Entries come back newest first; the chart wants oldest first, and only the latest one
  // gets a quick-undo button -- older entries are rare mistakes, not worth a delete row each.
  const visible = bodyweight?.filter((e) => !isHidden(`bodyweight:${e.id}`)) ?? []
  const latest = visible[0]
  const points = [...visible].reverse().map((e) => ({
    time: new Date(e.recorded_at).getTime(),
    weight: Math.round(convertWeight(e.weight, e.unit, settings.weight_unit) * 10) / 10,
  }))

  return (
    <Card className="space-y-3">
      <div className="flex gap-2">
        <input
          type="number"
          inputMode="decimal"
          value={newWeight}
          onChange={(e) => setNewWeight(e.target.value)}
          placeholder={`Today's weight (${settings.weight_unit})`}
          className="h-10 flex-1 rounded-md border border-border bg-bg px-2 text-sm"
        />
        <Button onClick={handleLogWeight} disabled={upsertBodyweight.isPending} title="Log today's body weight">
          Log
        </Button>
      </div>
      {logError && <p className="text-sm text-danger">{logError}</p>}

      {latest && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted">Latest: {formatDate(latest.recorded_at)}</span>
          <div className="flex items-center gap-3">
            <span className="font-medium">
              {formatWeight(
                Math.round(convertWeight(latest.weight, latest.unit, settings.weight_unit) * 10) / 10,
                settings.weight_unit,
              )}
            </span>
            <button
              onClick={() =>
                deleteWithUndo({
                  message: `Deleted ${formatDate(latest.recorded_at)} entry`,
                  hideKey: `bodyweight:${latest.id}`,
                  commit: () => deleteBodyweight.mutateAsync(latest.id),
                })
              }
              title={`Delete the ${formatDate(latest.recorded_at)} entry`}
              className="text-xs text-muted hover:text-danger"
            >
              Delete
            </button>
          </div>
        </div>
      )}

      {points.length < 2 ? (
        <p className="py-6 text-center text-sm text-muted">Log a few more entries to see a trend.</p>
      ) : (
        <div className="h-40 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
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
                dataKey="weight"
                domain={['auto', 'auto']}
                tick={{ fontSize: 11, fill: 'var(--color-muted)' }}
                axisLine={false}
                tickLine={false}
                width={40}
              />
              <Tooltip
                formatter={(value) => [formatWeight(Number(value), settings.weight_unit), 'weight']}
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
                dataKey="weight"
                stroke="var(--color-accent)"
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  )
}
