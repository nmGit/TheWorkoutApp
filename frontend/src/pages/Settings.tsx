import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useSettings, useUpdateSettings } from '../api/settings'
import { DurationInput } from '../components/DurationInput'
import { Card, PageTitle } from '../components/ui'
import type { DistanceUnit, Experience, ProgressionMethod, Theme, WeightUnit } from '../types'

const SECTIONS = [
  { to: 'general', label: 'General', hint: 'Units, theme, rest timer' },
  { to: 'generated-workouts', label: 'Generated Workouts', hint: 'Progression, rep range, experience' },
  { to: 'about', label: 'About & credits', hint: 'Data sources and licensing' },
]

export function SettingsMenuPage() {
  return (
    <div className="space-y-4">
      <PageTitle
        action={
          <a
            href="/docs/features/bodyweight_and_settings.html#settings"
            target="_blank"
            rel="noreferrer"
            title="Open the user manual's settings section"
            className="text-xs font-medium text-muted hover:text-accent"
          >
            Help
          </a>
        }
      >
        Settings
      </PageTitle>
      <Card className="space-y-1.5 p-2">
        {SECTIONS.map((s) => (
          <Link
            key={s.to}
            to={s.to}
            title={s.label}
            className="flex items-center justify-between rounded-lg px-3 py-3 text-left text-sm hover:bg-border/30"
          >
            <span>
              <span className="font-medium">{s.label}</span>
              <span className="block text-xs text-muted">{s.hint}</span>
            </span>
            <span className="text-muted" aria-hidden>
              ›
            </span>
          </Link>
        ))}
      </Card>
    </div>
  )
}

/** The section pages' shared header: a back link to the settings menu, a link into the user
 * manual's matching section, then the section's title. */
function SectionHeader({ children, docsHref }: { children: ReactNode; docsHref: string }) {
  return (
    <>
      <div className="flex items-center justify-between">
        <Link to="/settings" title="Back to Settings" className="text-xs font-medium text-muted hover:text-accent">
          ← Settings
        </Link>
        <a
          href={docsHref}
          target="_blank"
          rel="noreferrer"
          title="Open the matching section of the user manual"
          className="text-xs font-medium text-muted hover:text-accent"
        >
          Help
        </a>
      </div>
      <PageTitle>{children}</PageTitle>
    </>
  )
}

export function GeneralSettingsPage() {
  const { data: settings } = useSettings()
  const updateSettings = useUpdateSettings()
  if (!settings) return null

  return (
    <div className="space-y-4">
      <SectionHeader docsHref="/docs/features/bodyweight_and_settings.html#settings">General</SectionHeader>
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
            options={['system', 'light', 'dark', 'green', 'pink'] as Theme[]}
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
    </div>
  )
}

export function GeneratedWorkoutsSettingsPage() {
  const { data: settings } = useSettings()
  const updateSettings = useUpdateSettings()
  if (!settings) return null

  return (
    <div className="space-y-4">
      <SectionHeader docsHref="/docs/features/progressive_overload.html">Generated Workouts</SectionHeader>
      <Card className="space-y-3">
        <div>
          <h3 className="text-sm font-semibold">Progressive Overload</h3>
          <p className="mt-1 text-sm text-muted">
            {settings.progression_method === 'double'
              ? 'Double progression: add reps within the rep range, then add load and start again at the bottom of the range.'
              : settings.progression_method === 'linear'
                ? 'Linear progression: add load each time the target reps are reached.'
                : 'Off: each workout starts with the weights and reps of the last session.'}
          </p>
        </div>
        <Field label="Progression">
          <SegmentedControl
            label="progression"
            options={['double', 'linear', 'off'] as ProgressionMethod[]}
            value={settings.progression_method}
            onChange={(v) => updateSettings.mutate({ progression_method: v })}
          />
        </Field>
        {settings.progression_method !== 'off' && (
          <Field label="Default rep range">
            <RepRangeField
              value={settings.default_rep_range}
              onCommit={(v) => updateSettings.mutate({ default_rep_range: v })}
            />
          </Field>
        )}
        <Field label="Experience">
          <SegmentedControl
            label="experience"
            options={['novice', 'intermediate'] as Experience[]}
            value={settings.experience}
            onChange={(v) => updateSettings.mutate({ experience: v })}
          />
        </Field>
        <LoadStepField
          label="Load step (lb)"
          value={settings.load_step_lb}
          onCommit={(v) => updateSettings.mutate({ load_step_lb: v })}
        />
        <LoadStepField
          label="Load step (kg)"
          value={settings.load_step_kg}
          onCommit={(v) => updateSettings.mutate({ load_step_kg: v })}
        />
      </Card>
    </div>
  )
}

export function AboutSettingsPage() {
  return (
    <div className="space-y-4">
      <SectionHeader docsHref="/docs/features/exercise_library.html">About &amp; credits</SectionHeader>
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

/** A load step in the given unit. Saved when the field loses focus; values must be above zero. */
function LoadStepField({ label, value, onCommit }: { label: string; value: number; onCommit: (v: number) => void }) {
  const [text, setText] = useState(String(value))
  return (
    <Field label={label}>
      <input
        type="number"
        inputMode="decimal"
        min={0}
        step="any"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={() => {
          const parsed = Number(text)
          if (parsed > 0 && parsed !== value) onCommit(parsed)
          else setText(String(value))
        }}
        className="h-10 w-28 rounded-md border border-border bg-bg px-2 text-sm tabular-nums"
      />
    </Field>
  )
}

/** The rep range used when an exercise has none of its own, like "8-12". Saved when the field loses focus. */
function RepRangeField({ value, onCommit }: { value: string; onCommit: (v: string) => void }) {
  const [text, setText] = useState(value)
  return (
    <div className="space-y-1">
      <input
        value={text}
        placeholder="8-12"
        onChange={(e) => setText(e.target.value)}
        onBlur={() => {
          const next = text.trim()
          if (next && next !== value) onCommit(next)
          else setText(value)
        }}
        className="h-10 w-28 rounded-md border border-border bg-bg px-2 text-center text-sm tabular-nums"
      />
      <p className="text-xs text-muted">Each exercise can set its own range in its template.</p>
    </div>
  )
}
