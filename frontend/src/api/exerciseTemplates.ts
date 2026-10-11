import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { Equipment, ExerciseTemplate, MuscleGroup, MuscleOption, PlanPreviewSet, TrackingType, WorkoutSet } from '../types'

const INFINITE_PAGE_SIZE = 60

export interface ExerciseTemplateListParams {
  q?: string
  bodyPart?: string
  muscleGroupId?: number
  muscle?: string
  equipment?: string
  trackingType?: string
  limit?: number
  offset?: number
}

export const exerciseTemplateKeys = {
  all: ['exercise-templates'] as const,
  list: (params: ExerciseTemplateListParams) => ['exercise-templates', 'list', params] as const,
  detail: (id: number) => ['exercise-templates', 'detail', id] as const,
  history: (id: number) => ['exercise-templates', 'history', id] as const,
  planPreview: (id: number, params: PlanPreviewParams) => ['exercise-templates', 'plan-preview', id, params] as const,
  facets: ['exercise-templates', 'facets'] as const,
  muscleGroups: ['muscle-groups'] as const,
  groupMuscles: (groupId: number) => ['muscle-groups', groupId, 'muscles'] as const,
}

export interface ExerciseTemplateListResult {
  total: number
  items: ExerciseTemplate[]
}

function buildSearchParams(params: ExerciseTemplateListParams): URLSearchParams {
  const search = new URLSearchParams()
  if (params.q) search.set('q', params.q)
  if (params.bodyPart) search.set('body_part', params.bodyPart)
  if (params.muscleGroupId) search.set('muscle_group_id', String(params.muscleGroupId))
  if (params.muscle) search.set('muscle', params.muscle)
  if (params.equipment) search.set('equipment', params.equipment)
  if (params.trackingType) search.set('tracking_type', params.trackingType)
  return search
}

export function useMuscleGroups() {
  return useQuery({
    queryKey: exerciseTemplateKeys.muscleGroups,
    queryFn: () => api.get<MuscleGroup[]>('/muscle-groups'),
    staleTime: Infinity,
  })
}

export function useGroupMuscles(groupId: number | undefined) {
  return useQuery({
    queryKey: exerciseTemplateKeys.groupMuscles(groupId ?? 0),
    queryFn: () => api.get<MuscleOption[]>(`/muscle-groups/${groupId}/muscles`),
    enabled: groupId !== undefined,
    staleTime: Infinity,
  })
}

export function useExerciseTemplates(params: ExerciseTemplateListParams = {}) {
  const search = buildSearchParams(params)
  search.set('limit', String(params.limit ?? 30))
  search.set('offset', String(params.offset ?? 0))

  return useQuery({
    queryKey: exerciseTemplateKeys.list(params),
    queryFn: () => api.get<ExerciseTemplateListResult>(`/exercise-templates?${search.toString()}`),
  })
}

/** Paginates by accumulating pages, since the backend caps `limit` per
 * request -- naively raising `limit` on "load more" would silently stop
 * making progress once it hit that cap while `total` still claimed more
 * were available. */
export function useInfiniteExerciseTemplates(
  params: Omit<ExerciseTemplateListParams, 'limit' | 'offset'> = {},
) {
  return useInfiniteQuery({
    queryKey: ['exercise-templates', 'infinite', params],
    queryFn: ({ pageParam }) => {
      const search = buildSearchParams(params)
      search.set('limit', String(INFINITE_PAGE_SIZE))
      search.set('offset', String(pageParam))
      return api.get<ExerciseTemplateListResult>(`/exercise-templates?${search.toString()}`)
    },
    initialPageParam: 0,
    getNextPageParam: (_lastPage, allPages) => {
      const loaded = allPages.reduce((sum, p) => sum + p.items.length, 0)
      const total = allPages[0]?.total ?? 0
      return loaded < total ? loaded : undefined
    },
  })
}

export function useExerciseTemplate(id: number | undefined) {
  return useQuery({
    queryKey: exerciseTemplateKeys.detail(id ?? -1),
    queryFn: () => api.get<ExerciseTemplate>(`/exercise-templates/${id}`),
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
    queryKey: exerciseTemplateKeys.history(id ?? -1),
    queryFn: () => api.get<{ total: number; items: ExerciseHistoryItem[] }>(`/exercise-templates/${id}/history`),
    enabled: id !== undefined,
  })
}

export interface PlanPreviewParams {
  warmupSets: number
  targetSets: number
  dropSets: number
  targetReps: string | null
}

/** What starting a workout with this exercise would plan right now -- the same progressive
 * overload calculation a real workout start uses, run against a hypothetical (possibly not yet
 * saved) set plan. Powers the template editor's preview. */
export function useExercisePlanPreview(id: number | undefined, params: PlanPreviewParams) {
  const search = new URLSearchParams()
  search.set('warmup_sets', String(params.warmupSets))
  search.set('target_sets', String(params.targetSets))
  search.set('drop_sets', String(params.dropSets))
  if (params.targetReps) search.set('target_reps', params.targetReps)
  return useQuery({
    queryKey: exerciseTemplateKeys.planPreview(id ?? -1, params),
    queryFn: () => api.get<PlanPreviewSet[]>(`/exercise-templates/${id}/plan-preview?${search}`),
    enabled: id !== undefined,
  })
}

export function useExerciseTemplateFacets() {
  return useQuery({
    queryKey: exerciseTemplateKeys.facets,
    queryFn: () => api.get<{ body_parts: string[]; equipment: string[] }>('/exercise-templates/facets'),
    staleTime: Infinity,
  })
}

export function useCreateExerciseTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: {
      name: string
      muscle_group_id: number
      equipment?: Equipment
      tracking_type?: TrackingType
      notes?: string
    }) => api.post<ExerciseTemplate>('/exercise-templates', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: exerciseTemplateKeys.all }),
  })
}

export function useUpdateExerciseTemplate(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<ExerciseTemplate>) => api.patch<ExerciseTemplate>(`/exercise-templates/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: exerciseTemplateKeys.all })
      qc.invalidateQueries({ queryKey: exerciseTemplateKeys.detail(id) })
    },
  })
}

export function useDeleteExerciseTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.delete(`/exercise-templates/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: exerciseTemplateKeys.all }),
  })
}
