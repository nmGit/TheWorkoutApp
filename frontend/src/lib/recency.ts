import type { Muscle } from '@abdofallah/musclemap-js'
import { ALL_REGIONS, withSubRegions } from './strengthColors'
import type { RegionFill } from './strengthColors'
import type { MuscleRecency } from '../api/recency'

/** Colour for how long ago a muscle was last worked: green up to 2 days, red from 8 days, and
 * a linear fade between them through the hue wheel, so the middle is yellow. (A straight RGB
 * blend of green and red is olive-brown, not yellow.) */
const GREEN_HUE = 142 // degrees; the hue of the green used elsewhere in the app
const RED_HUE = 0
const SATURATION = 0.8
const VALUE = 0.75
const FRESH_DAYS = 2
const STALE_DAYS = 8
export const NEVER_OPACITY = 0.35
export const NEVER_COLOR = '#6b7280'

function hsvToRgb(h: number, s: number, v: number): [number, number, number] {
  const c = v * s
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1))
  const m = v - c
  const [r, g, b] = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x] : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x]
  return [Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((b + m) * 255)]
}

export function recencyColor(days: number): string {
  const t = Math.max(0, Math.min(1, (days - FRESH_DAYS) / (STALE_DAYS - FRESH_DAYS)))
  const hue = GREEN_HUE + (RED_HUE - GREEN_HUE) * t
  const [r, g, b] = hsvToRgb(hue, SATURATION, VALUE)
  return `rgb(${r}, ${g}, ${b})`
}

/** One fill per body region, from the most recent of the muscles that map to it. */
export function recencyFills(muscles: Record<string, MuscleRecency> | undefined): RegionFill[] {
  const freshest = new Map<Muscle, number>()
  for (const info of Object.values(muscles ?? {})) {
    for (const region of info.regions) {
      const current = freshest.get(region)
      if (current === undefined || info.days_since < current) freshest.set(region, info.days_since)
    }
  }
  return withSubRegions(ALL_REGIONS.map((region) => {
    const days = freshest.get(region)
    if (days === undefined) return { region, color: NEVER_COLOR, opacity: NEVER_OPACITY, hasData: false }
    return { region, color: recencyColor(days), opacity: 0.9, hasData: true }
  }))
}
