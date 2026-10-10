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
  // Format the size, then add the sign: flooring a negative number gives the wrong minutes.
  const size = Math.abs(totalSeconds)
  const m = Math.floor(size / 60)
  const s = size % 60
  const sign = totalSeconds < 0 ? '-' : ''
  return `${sign}${m}:${String(s).padStart(2, '0')}`
}

/** How long a finished workout took, as "52m" or "1h 05m". Null while it's still running. */
export function formatWorkoutDuration(startedAt: string, completedAt: string | null): string | null {
  if (!completedAt) return null
  const minutes = Math.max(
    0,
    Math.round((new Date(completedAt).getTime() - new Date(startedAt).getTime()) / 60000),
  )
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return hours > 0 ? `${hours}h ${String(rest).padStart(2, '0')}m` : `${rest}m`
}

/** A rest duration as M:SS ("1:30", "0:45"), the way the rest timer counts. */
export function formatRest(totalSeconds: number): string {
  const safe = Math.max(0, Math.round(totalSeconds))
  return `${Math.floor(safe / 60)}:${String(safe % 60).padStart(2, '0')}`
}

/** Parse what someone types into a rest field: "1:30" (minutes:seconds) or a
 * bare number of seconds ("90"). Empty means "no value" (null); anything
 * else that doesn't parse is undefined. */
export function parseRest(text: string): number | null | undefined {
  const t = text.trim()
  if (t === '') return null
  const mmss = /^(\d{1,3}):(\d{1,2})$/.exec(t)
  if (mmss) {
    const seconds = Number(mmss[2])
    return seconds < 60 ? Number(mmss[1]) * 60 + seconds : undefined
  }
  return /^\d{1,5}$/.test(t) ? Number(t) : undefined
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
