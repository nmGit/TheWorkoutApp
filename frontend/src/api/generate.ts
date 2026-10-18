import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import { invalidateWorkout } from './workouts'
import type { Workout } from '../types'

export interface GenerateOptions {
  count: number
  stretching: boolean
  cardio: boolean
  /** Use exercises the person has done before, falling back to others only when needed. */
  familiarFirst: boolean
  /** The training groups to work, in the order shown. */
  groups: string[]
}

export interface GroupRank {
  name: string
  /** How many of the group's current muscles are in need of training. */
  in_need: number
  /** How many of the group's muscles are part of current training. */
  trained: number
}

/** The training groups, most in need first. Fetched when the generate panel opens. */
export function useGenerateGroups(enabled: boolean) {
  return useQuery({
    queryKey: ['generate-groups'],
    queryFn: () => api.get<GroupRank[]>('/workouts/generate/groups'),
    enabled,
  })
}

export function useGenerateWorkout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (options: GenerateOptions) =>
      api.post<Workout>('/workouts/generated', {
        count: options.count,
        stretching: options.stretching,
        cardio: options.cardio,
        familiar_first: options.familiarFirst,
        groups: options.groups,
      }),
    onSuccess: () => invalidateWorkout(qc),
  })
}
