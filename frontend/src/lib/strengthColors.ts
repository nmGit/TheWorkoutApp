import type { Muscle } from '@abdofallah/musclemap-js'
import { regionsFor } from './muscleMap'
import type { MuscleSummary, WorkoutStrength } from '../types'

/**
 * Every region we colour. Each gets a fill, so regions with no data show grey.
 * Excluded: the hidden sub-groups (see lib/muscleMap.ts), and head and knees, which
 * the widget draws in their own colours and which would be dimmed by a fill.
 */
export const ALL_REGIONS: Muscle[] = [
  'abs', 'biceps', 'calves', 'chest', 'deltoids', 'feet', 'forearm', 'gluteal', 'hamstring',
  'hands', 'lower-back', 'obliques', 'quadriceps', 'tibialis', 'trapezius', 'triceps',
  'upper-back', 'rotator-cuff', 'serratus', 'rhomboids',
  // Always-visible sub-groups, so the widget draws them even with sub-groups hidden.
  'ankles', 'adductors', 'neck',
]

/** A ratio this far from 1.0 (here ±10%) gets the full colour. */
export const SATURATION = 0.1

export const COLORS = {
  neutral: [229, 231, 235] as const, // no change
  improved: [22, 163, 74] as const, // green
  regressed: [220, 38, 38] as const, // red
  pending: '#3b82f6', // blue: planned or skipped, not done yet
  noData: '#6b7280', // grey, dark enough to read apart from "no change"
}

const NO_DATA_OPACITY = 0.5
const DATA_OPACITY = 0.9

export interface RegionFill {
  region: Muscle
  color: string
  opacity: number
}

/** The colour for a strength ratio: red below 1.0, green above, fading to neutral near 1.0. */
export function strengthColor(ratio: number): string {
  const scaled = Math.max(-1, Math.min(1, Math.log(ratio) / Math.log(1 + SATURATION)))
  const target = scaled >= 0 ? COLORS.improved : COLORS.regressed
  const t = Math.abs(scaled)
  const [r, g, b] = COLORS.neutral.map((c, i) => Math.round(c + (target[i] - c) * t))
  return `rgb(${r}, ${g}, ${b})`
}

/** One fill per region. A region worked by several muscles averages their scored
 * ratios (geometric mean). It's blue only when planned but not yet worked: a region
 * with any counting set this workout, even one without a baseline yet, is not blue.
 * Otherwise it's grey. */
export function strengthFills(strength: WorkoutStrength | undefined): RegionFill[] {
  const byRegion = new Map<Muscle, { ratios: number[]; pending: boolean; worked: boolean }>()
  for (const [slug, m] of Object.entries(strength?.muscles ?? {})) {
    for (const region of regionsFor(slug)) {
      const entry = byRegion.get(region) ?? { ratios: [], pending: false, worked: false }
      if (m.status === 'scored' && m.ratio !== null) entry.ratios.push(m.ratio)
      if (m.status === 'pending') entry.pending = true
      if (m.status === 'scored' || m.status === 'no_baseline') entry.worked = true
      byRegion.set(region, entry)
    }
  }
  return ALL_REGIONS.map((region) => {
    const entry = byRegion.get(region)
    if (entry && entry.ratios.length > 0) {
      const geometric = Math.exp(entry.ratios.reduce((sum, r) => sum + Math.log(r), 0) / entry.ratios.length)
      return { region, color: strengthColor(geometric), opacity: DATA_OPACITY }
    }
    if (entry?.pending && !entry.worked) return { region, color: COLORS.pending, opacity: DATA_OPACITY }
    return { region, color: COLORS.noData, opacity: NO_DATA_OPACITY }
  })
}

/** Fills for a template with no completed instance yet: every region it works is pure
 * blue (planned, not done), and the rest is grey. */
export function templateFills(muscles: MuscleSummary): RegionFill[] {
  const planned = new Set<Muscle>()
  for (const slug of [...muscles.primary, ...muscles.secondary]) {
    for (const region of regionsFor(slug)) planned.add(region)
  }
  return ALL_REGIONS.map((region) =>
    planned.has(region)
      ? { region, color: COLORS.pending, opacity: DATA_OPACITY }
      : { region, color: COLORS.noData, opacity: NO_DATA_OPACITY },
  )
}
