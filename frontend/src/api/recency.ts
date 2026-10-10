import type { Muscle } from '@abdofallah/musclemap-js'
import { useQuery } from '@tanstack/react-query'
import { api } from './client'

/** When one muscle was last worked. */
export interface MuscleRecency {
  /** Local calendar date (YYYY-MM-DD) of the last working set. */
  last_trained: string
  days_since: number
  regions: Muscle[]
}

export interface MuscleRecencyResponse {
  /** Days since training at which a muscle counts as in need of training (from the backend). */
  in_need_days: number
  /** Keyed by canonical muscle slug. A muscle never worked is absent. */
  muscles: Record<string, MuscleRecency>
}

export function useMuscleRecency() {
  return useQuery({
    queryKey: ['muscle-recency'],
    queryFn: () => api.get<MuscleRecencyResponse>('/muscles/recency'),
  })
}
