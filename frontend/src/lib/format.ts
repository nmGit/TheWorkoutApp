import type { WeightUnit } from '../types'
import { convertWeight } from './units'

export function formatWeight(value: number | null | undefined, unit: string | null | undefined): string {
  if (value === null || value === undefined) return '-'
  const rounded = Math.round(value * 10) / 10
  return `${rounded}${unit ?? ''}`
}

export function formatDate(iso: string): string {
  const d = new Date(iso.length <= 10 ? `${iso}T00:00:00` : iso)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

export function formatShortDate(iso: string): string {
  const d = new Date(iso.length <= 10 ? `${iso}T00:00:00` : iso)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function formatDuration(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60)
  const s = Math.abs(totalSeconds % 60)
  const sign = totalSeconds < 0 ? '-' : ''
  return `${sign}${m}:${String(s).padStart(2, '0')}`
}

export function formatElapsed(startedAt: string): string {
  const started = new Date(startedAt).getTime()
  const now = Date.now()
  const totalMinutes = Math.max(0, Math.floor((now - started) / 60000))
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`
}

export function setSummary(
  set: {
    weight: number | null
    weight_unit: WeightUnit | null
    reps: number | null
    duration_seconds: number | null
    distance_meters: number | null
  },
  displayUnit: WeightUnit,
): string {
  if (set.weight !== null && set.reps !== null) {
    const converted = convertWeight(set.weight, set.weight_unit, displayUnit)
    return `${set.reps} × ${formatWeight(Math.round(converted * 10) / 10, displayUnit)}`
  }
  if (set.reps !== null) return `${set.reps} reps`
  if (set.duration_seconds !== null) return formatDuration(set.duration_seconds)
  return '-'
}
