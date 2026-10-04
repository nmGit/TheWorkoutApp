import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { StrengthPoint, Workout, WorkoutExercise, WorkoutSet, WorkoutStrength, WorkoutSummary } from '../types'

export const workoutKeys = {
  all: ['workouts'] as const,
  list: (params: Record<string, string | number | undefined>) => ['workouts', 'list', params] as const,
  active: ['workouts', 'active'] as const,
  detail: (id: number) => ['workouts', 'detail', id] as const,
  strength: (id: number) => ['workouts', 'strength', id] as const,
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
  return Promise.all([
    qc.invalidateQueries({ queryKey: workoutKeys.active }),
    qc.invalidateQueries({ queryKey: ['workouts', 'list'] }),
    id !== undefined ? qc.invalidateQueries({ queryKey: workoutKeys.detail(id) }) : undefined,
    // Editing a workout also changes the baselines of every later workout, so every
    // strength query is stale, not just this one's.
    qc.invalidateQueries({ queryKey: ['workouts', 'strength'] }),
    qc.invalidateQueries({ queryKey: ['strength-history'] }),
  ])
}

export function useStrengthHistory() {
  return useQuery({
    queryKey: ['strength-history'],
    queryFn: () => api.get<StrengthPoint[]>('/strength/history'),
  })
}

export function useWorkoutStrength(id: number | undefined) {
  return useQuery({
    queryKey: workoutKeys.strength(id ?? -1),
    queryFn: () => api.get<WorkoutStrength>(`/workouts/${id}/strength`),
    enabled: id !== undefined,
  })
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

export function useUpdateWorkoutExercise(workoutId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ workoutExerciseId, notes }: { workoutExerciseId: number; notes: string }) =>
      api.patch<Workout>(`/workouts/${workoutId}/exercises/${workoutExerciseId}`, { notes }),
    onSuccess: () => invalidateWorkout(qc, workoutId),
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

/** Optimistic, unlike the other mutations here: the drag gesture already
 * shows the new order live via direct DOM transforms (see
 * `useDragReorder`), but those transforms are cleared the instant the
 * gesture ends -- without writing the reordered list into the cache
 * immediately, the list would visibly snap back to the old order for the
 * length of the round-trip. */
export function useReorderWorkoutExercises(workoutId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (exerciseIds: number[]) =>
      api.patch<Workout>(`/workouts/${workoutId}/exercises/reorder`, { exercise_ids: exerciseIds }),
    onMutate: async (exerciseIds: number[]) => {
      await qc.cancelQueries({ queryKey: workoutKeys.active })
      const previous = qc.getQueryData<Workout | null>(workoutKeys.active)
      if (previous) {
        const byId = new Map(previous.exercises.map((we) => [we.id, we]))
        const reordered = exerciseIds
          .map((id) => byId.get(id))
          .filter((we): we is WorkoutExercise => we !== undefined)
        qc.setQueryData<Workout>(workoutKeys.active, { ...previous, exercises: reordered })
      }
      return { previous }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous !== undefined) qc.setQueryData(workoutKeys.active, context.previous)
    },
    onSettled: () => invalidateWorkout(qc, workoutId),
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
