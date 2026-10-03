import { useState, type ReactNode } from 'react'
import {
  useBodyweightEntries,
  useDeleteBodyweight,
  useSettings,
  useUpdateSettings,
  useUpsertBodyweight,
} from '../api/settings'
import { DurationInput } from '../components/DurationInput'
import { Button, Card, PageTitle } from '../components/ui'
import { formatDate, formatWeight } from '../lib/format'
import { convertWeight } from '../lib/units'
import type { DistanceUnit, Theme, WeightUnit } from '../types'

export function SettingsPage() {
  const { data: settings } = useSettings()
  const updateSettings = useUpdateSettings()
  const { data: bodyweight } = useBodyweightEntries()
  const upsertBodyweight = useUpsertBodyweight()
  const deleteBodyweight = useDeleteBodyweight()
  const [newWeight, setNewWeight] = useState('')

  if (!settings) return null

  const handleLogWeight = () => {
    if (!newWeight) return
    upsertBodyweight.mutate({ weight: Number(newWeight) })
    setNewWeight('')
  }

  return (
    <div className="space-y-4">
      <PageTitle>Settings</PageTitle>

      <Card className="space-y-4">
        <Field label="Weight unit">
          <SegmentedControl
            label="weight unit"
            options={['lbs', 'kg'] as WeightUnit[]}
            value={settings.weight_unit}
            onChange={(v) => updateSettings.mutate({ weight_unit: v })}
          />
        </Field>
        <Field label="Distance unit">
          <SegmentedControl
            label="distance unit"
            options={['mi', 'km'] as DistanceUnit[]}
            value={settings.distance_unit}
            onChange={(v) => updateSettings.mutate({ distance_unit: v })}
          />
        </Field>
        <Field label="Theme">
          <SegmentedControl
            label="theme"
            options={['system', 'light', 'dark'] as Theme[]}
            value={settings.theme}
            onChange={(v) => updateSettings.mutate({ theme: v })}
          />
        </Field>
        <Field label="Default rest timer (m:ss)">
          <DurationInput
            value={settings.default_rest_seconds}
            onCommit={(seconds) => seconds !== null && updateSettings.mutate({ default_rest_seconds: seconds })}
            label="Default rest timer (m:ss)"
            title="Used when an exercise has no rest history yet (m:ss, or seconds)"
            className="h-10 w-24 rounded-md border border-border bg-bg px-2 text-center text-sm tabular-nums"
          />
        </Field>
      </Card>

      <div>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted">Body weight</h2>
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
          <div className="divide-y divide-border">
            {bodyweight?.slice(0, 10).map((entry) => (
              <div key={entry.id} className="flex items-center justify-between py-2 text-sm">
                <span className="text-muted">{formatDate(entry.recorded_at)}</span>
                <span className="font-medium">
                  {formatWeight(
                    Math.round(convertWeight(entry.weight, entry.unit, settings.weight_unit) * 10) / 10,
                    settings.weight_unit,
                  )}
                </span>
                <button
                  onClick={() => deleteBodyweight.mutate(entry.id)}
                  title={`Delete the ${formatDate(entry.recorded_at)} entry`}
                  className="text-xs text-muted hover:text-danger"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted">About &amp; credits</h2>
        <Card className="space-y-2 text-sm">
          <p>
            Exercise data by{' '}
            <a href="https://repdb.co" target="_blank" rel="noreferrer" className="underline">
              RepDB (repdb.co)
            </a>
            : illustrations, instructions, tips and muscle diagrams.
          </p>
          <p>
            Additional exercise data from the{' '}
            <a
              href="https://github.com/hasaneyldrm/exercises-dataset"
              target="_blank"
              rel="noreferrer"
              className="underline"
            >
              exercises-dataset
            </a>
            ; images © Gym visual,{' '}
            <a href="https://gymvisual.com/" target="_blank" rel="noreferrer" className="underline">
              gymvisual.com
            </a>
            .
          </p>
        </Card>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-sm text-fg">{label}</span>
      {children}
    </div>
  )
}

function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: T[]
  value: T
  onChange: (value: T) => void
  label?: string
}) {
  return (
    <div className="flex rounded-lg border border-border p-0.5">
      {options.map((opt) => (
        <button
          key={opt}
          onClick={() => onChange(opt)}
          title={`Set ${label ?? 'this'} to ${opt}`}
          className={`rounded-md px-3 py-1.5 text-xs font-medium capitalize ${
            value === opt ? 'bg-accent text-accent-fg' : 'text-muted'
          }`}
        >
          {opt}
        </button>
      ))}
    </div>
  )
}
