import { useQuery } from '@tanstack/react-query'
import { api } from './client'
import { refParts, type ExerciseRef } from '../lib/exerciseRef'
import type { DashboardStats, ExerciseStats } from '../types'

export function useExerciseStats(ref: Partial<ExerciseRef> | undefined, metric?: string, range = 'all') {
  const { id, isCustom } = refParts(ref)
  const search = new URLSearchParams({ range })
  if (metric) search.set('metric', metric)
  const path = isCustom ? `/custom-exercises/${id}/stats` : `/exercises/${id}/stats`
  return useQuery({
    queryKey: ['exercise-stats', id, isCustom, metric, range],
    queryFn: () => api.get<ExerciseStats>(`${path}?${search.toString()}`),
    enabled: id !== undefined,
  })
}

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get<DashboardStats>('/stats/dashboard'),
  })
}

export function useBodyweightStats(range = 'all') {
  return useQuery({
    queryKey: ['bodyweight-stats', range],
    queryFn: () => api.get<{ date: string; weight: number }[]>(`/stats/bodyweight?range=${range}`),
  })
}
