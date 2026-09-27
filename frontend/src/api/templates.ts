import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { WorkoutTemplate } from '../types'

export const templateKeys = {
  all: ['templates'] as const,
  detail: (id: number) => ['templates', 'detail', id] as const,
}

export function useTemplates() {
  return useQuery({
    queryKey: templateKeys.all,
    queryFn: () => api.get<WorkoutTemplate[]>('/templates'),
  })
}

export function useTemplate(id: number | undefined) {
  return useQuery({
    queryKey: templateKeys.detail(id ?? -1),
    queryFn: () => api.get<WorkoutTemplate>(`/templates/${id}`),
    enabled: id !== undefined,
  })
}

export interface TemplateExerciseInput {
  exercise_id: number
  target_sets?: number | null
  target_reps?: string | null
  target_weight?: number | null
}

export function useCreateTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; notes?: string; exercises: TemplateExerciseInput[] }) =>
      api.post<WorkoutTemplate>('/templates', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: templateKeys.all }),
  })
}

export function useUpdateTemplate(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name?: string; notes?: string; exercises?: TemplateExerciseInput[] }) =>
      api.patch<WorkoutTemplate>(`/templates/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: templateKeys.all })
      qc.invalidateQueries({ queryKey: templateKeys.detail(id) })
    },
  })
}

export function useDeleteTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.delete(`/templates/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: templateKeys.all }),
  })
}

export function useCreateTemplateFromWorkout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (workoutId: number) =>
      api.post<WorkoutTemplate>(`/templates/from-workout/${workoutId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: templateKeys.all }),
  })
}
