import type { WeightUnit } from '../types'

const LBS_PER_KG = 2.20462262185

/** Mirrors backend/app/services/units.py convert_weight — never mutates
 * stored values, only converts for display (or for re-storing a value the
 * user just typed while viewing in a different unit than it was logged in). */
export function convertWeight(
  value: number,
  fromUnit: WeightUnit | null | undefined,
  toUnit: WeightUnit,
): number {
  if (!fromUnit || fromUnit === toUnit) return value
  if (fromUnit === 'lbs' && toUnit === 'kg') return value / LBS_PER_KG
  if (fromUnit === 'kg' && toUnit === 'lbs') return value * LBS_PER_KG
  return value
}
