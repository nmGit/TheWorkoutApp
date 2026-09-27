import { useQuery } from '@tanstack/react-query'
import { api } from './client'
import type { DashboardStats, ExerciseStats } from '../types'

export function useExerciseStats(id: number | undefined, metric?: string, range = 'all') {
  const search = new URLSearchParams({ range })
  if (metric) search.set('metric', metric)
  return useQuery({
    queryKey: ['exercise-stats', id, metric, range],
    queryFn: () => api.get<ExerciseStats>(`/exercises/${id}/stats?${search.toString()}`),
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
