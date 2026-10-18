import type { Muscle } from '@abdofallah/musclemap-js'
import type { MuscleSummary, WorkoutStrength } from '../types'

/**
 * Every region we colour. Each gets a fill, so regions with no data show grey. Head and knees are
 * left out: the widget draws them in their own colours, and a fill would dim them.
 */
export const ALL_REGIONS: Muscle[] = [
  'abs', 'biceps', 'calves', 'chest', 'deltoids', 'feet', 'forearm', 'gluteal', 'hamstring',
  'hands', 'lower-back', 'obliques', 'quadriceps', 'tibialis', 'trapezius', 'triceps',
  'upper-back', 'rotator-cuff', 'serratus', 'rhomboids',
  // Sub-regions, drawn because the widget shows sub-groups.
  'front-deltoid', 'rear-deltoid', 'upper-chest', 'hip-flexors', 'upper-trapezius',
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
 * ratios (geometric mean). A region that was worked or planned but has no score yet is
 * blue. A region nothing in the workout touches is grey. */
export function strengthFills(strength: WorkoutStrength | undefined): RegionFill[] {
  const byRegion = new Map<Muscle, { ratios: number[]; pending: boolean; worked: boolean }>()
  for (const m of Object.values(strength?.muscles ?? {})) {
    for (const region of m.regions) {
      const entry = byRegion.get(region) ?? { ratios: [], pending: false, worked: false }
      if (m.status === 'scored' && m.ratio !== null) entry.ratios.push(m.ratio)
      if (m.status === 'pending') entry.pending = true
      if (m.status === 'scored' || m.status === 'no_baseline') entry.worked = true
      byRegion.set(region, entry)
    }
  }
  return withSubRegions(ALL_REGIONS.map((region) => {
    const entry = byRegion.get(region)
    if (entry && entry.ratios.length > 0) {
      const geometric = Math.exp(entry.ratios.reduce((sum, r) => sum + Math.log(r), 0) / entry.ratios.length)
      return { region, color: strengthColor(geometric), opacity: DATA_OPACITY, hasData: true }
    }
    // Worked or planned but not scored yet: blue, so the workout still shows its muscles.
    if (entry && (entry.worked || entry.pending)) return { region, color: COLORS.pending, opacity: DATA_OPACITY, hasData: true }
    return { region, color: COLORS.noData, opacity: NO_DATA_OPACITY, hasData: false }
  }))
}

/** Fills for a template with no completed instance yet: every region it works is pure
 * blue (planned, not done), and the rest is grey. */
export function templateFills(muscles: MuscleSummary): RegionFill[] {
  const planned = new Set<Muscle>(muscles.regions)
  return withSubRegions(ALL_REGIONS.map((region) =>
    planned.has(region)
      ? { region, color: COLORS.pending, opacity: DATA_OPACITY, hasData: true }
      : { region, color: COLORS.noData, opacity: NO_DATA_OPACITY, hasData: false },
  ))
}

/** Sub-regions of the diagram (upper chest, rear deltoid, upper abs, ...). The widget draws them over
 * their parent region, so one without data must not get a fill of its own: it inherits its parent's
 * colour instead. */
export const SUB_REGIONS = new Set<string>([
  'ankles', 'adductors', 'neck', 'hip-flexors', 'upper-chest', 'lower-chest', 'inner-quad', 'outer-quad',
  'upper-abs', 'lower-abs', 'front-deltoid', 'rear-deltoid', 'upper-trapezius', 'lower-trapezius',
])

/** Drop the fills of sub-regions that have no data, and strip the bookkeeping flag. */
export function withSubRegions(fills: (RegionFill & { hasData: boolean })[]): RegionFill[] {
  return fills
    .filter((f) => f.hasData || !SUB_REGIONS.has(f.region))
    .map(({ region, color, opacity }) => ({ region, color, opacity }))
}
