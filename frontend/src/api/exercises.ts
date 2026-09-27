import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { Equipment, Exercise, MuscleGroup, TrackingType, WorkoutSet } from '../types'

export const exerciseKeys = {
  all: ['exercises'] as const,
  list: (params: { q?: string; muscleGroupId?: number; equipment?: string }) =>
    ['exercises', 'list', params] as const,
  detail: (id: number) => ['exercises', 'detail', id] as const,
  history: (id: number) => ['exercises', 'history', id] as const,
  muscleGroups: ['muscle-groups'] as const,
}

export function useMuscleGroups() {
  return useQuery({
    queryKey: exerciseKeys.muscleGroups,
    queryFn: () => api.get<MuscleGroup[]>('/muscle-groups'),
    staleTime: Infinity,
  })
}

export function useExercises(params: { q?: string; muscleGroupId?: number; equipment?: string } = {}) {
  const search = new URLSearchParams()
  if (params.q) search.set('q', params.q)
  if (params.muscleGroupId) search.set('muscle_group_id', String(params.muscleGroupId))
  if (params.equipment) search.set('equipment', params.equipment)

  return useQuery({
    queryKey: exerciseKeys.list(params),
    queryFn: () => api.get<Exercise[]>(`/exercises?${search.toString()}`),
  })
}

export function useExercise(id: number | undefined) {
  return useQuery({
    queryKey: exerciseKeys.detail(id ?? -1),
    queryFn: () => api.get<Exercise>(`/exercises/${id}`),
    enabled: id !== undefined,
  })
}

export interface ExerciseHistoryItem {
  workout_id: number
  date: string
  notes: string | null
  sets: WorkoutSet[]
}

export function useExerciseHistory(id: number | undefined) {
  return useQuery({
    queryKey: exerciseKeys.history(id ?? -1),
    queryFn: () => api.get<{ total: number; items: ExerciseHistoryItem[] }>(`/exercises/${id}/history`),
    enabled: id !== undefined,
  })
}

export function useCreateExercise() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: {
      name?: string
      muscle_group_id?: number
      equipment?: Equipment
      tracking_type?: TrackingType
      default_rest_seconds?: number
      notes?: string
      template_id?: number
    }) => api.post<Exercise>('/exercises', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: exerciseKeys.all }),
  })
}

export function useUpdateExercise(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Exercise>) => api.patch<Exercise>(`/exercises/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: exerciseKeys.all })
      qc.invalidateQueries({ queryKey: exerciseKeys.detail(id) })
    },
  })
}

export function useDeleteExercise() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.delete(`/exercises/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: exerciseKeys.all }),
  })
}
