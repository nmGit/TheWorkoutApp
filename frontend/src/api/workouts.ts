import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { Workout, WorkoutSet, WorkoutSummary } from '../types'

export const workoutKeys = {
  all: ['workouts'] as const,
  list: (params: Record<string, string | number | undefined>) => ['workouts', 'list', params] as const,
  active: ['workouts', 'active'] as const,
  detail: (id: number) => ['workouts', 'detail', id] as const,
}

export function useActiveWorkout() {
  return useQuery({
    queryKey: workoutKeys.active,
    queryFn: async () => {
      const res = await fetch('/api/workouts/active')
      if (res.status === 204) return null
      if (!res.ok) throw new Error('Failed to load active workout')
      return (await res.json()) as Workout
    },
    refetchOnWindowFocus: true,
  })
}

export function useWorkouts(params: { status?: string; limit?: number } = {}) {
  const search = new URLSearchParams()
  if (params.status) search.set('status', params.status)
  if (params.limit) search.set('limit', String(params.limit))
  return useQuery({
    queryKey: workoutKeys.list(params),
    queryFn: () => api.get<WorkoutSummary[]>(`/workouts?${search.toString()}`),
  })
}

export function useWorkout(id: number | undefined) {
  return useQuery({
    queryKey: workoutKeys.detail(id ?? -1),
    queryFn: () => api.get<Workout>(`/workouts/${id}`),
    enabled: id !== undefined,
  })
}

function invalidateWorkout(qc: ReturnType<typeof useQueryClient>, id?: number) {
  qc.invalidateQueries({ queryKey: workoutKeys.active })
  qc.invalidateQueries({ queryKey: ['workouts', 'list'] })
  if (id !== undefined) qc.invalidateQueries({ queryKey: workoutKeys.detail(id) })
}

export function useStartWorkout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (templateId?: number) =>
      api.post<Workout>('/workouts', templateId ? { template_id: templateId } : {}),
    onSuccess: (workout) => invalidateWorkout(qc, workout.id),
  })
}

export function useUpdateWorkout(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name?: string; notes?: string; body_weight?: number; finish?: boolean }) =>
      api.patch<Workout>(`/workouts/${id}`, data),
    onSuccess: () => invalidateWorkout(qc, id),
  })
}

export function useDeleteWorkout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.delete(`/workouts/${id}`),
    onSuccess: (_data, id) => invalidateWorkout(qc, id),
  })
}

export function useAddWorkoutExercise(workoutId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (exerciseId: number) =>
      api.post<Workout>(`/workouts/${workoutId}/exercises`, { exercise_id: exerciseId }),
    onSuccess: () => invalidateWorkout(qc, workoutId),
  })
}

export function useRemoveWorkoutExercise(workoutId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (workoutExerciseId: number) =>
      api.delete(`/workouts/${workoutId}/exercises/${workoutExerciseId}`),
    onSuccess: () => invalidateWorkout(qc, workoutId),
  })
}

export function useAddSet(workoutId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (workoutExerciseId: number) =>
      api.post<WorkoutSet>(`/workout-exercises/${workoutExerciseId}/sets`, {}),
    onSuccess: () => invalidateWorkout(qc, workoutId),
  })
}

export function useUpdateSet(workoutId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ setId, data }: { setId: number; data: Partial<WorkoutSet> }) =>
      api.patch<WorkoutSet>(`/sets/${setId}`, data),
    onSuccess: () => invalidateWorkout(qc, workoutId),
  })
}

export function useDeleteSet(workoutId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (setId: number) => api.delete(`/sets/${setId}`),
    onSuccess: () => invalidateWorkout(qc, workoutId),
  })
}
