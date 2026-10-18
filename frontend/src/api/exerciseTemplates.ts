import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import { refParts, type ExerciseRef } from '../lib/exerciseRef'
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
  detail: (id: number, isCustom = false) => ['exercise-templates', 'detail', id, isCustom] as const,
  history: (id: number, isCustom = false) => ['exercise-templates', 'history', id, isCustom] as const,
  planPreview: (id: number, isCustom: boolean, params: PlanPreviewParams) =>
    ['exercise-templates', 'plan-preview', id, isCustom, params] as const,
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

export function useExerciseTemplate(ref: Partial<ExerciseRef> | undefined) {
  const { id, isCustom } = refParts(ref)
  return useQuery({
    queryKey: exerciseTemplateKeys.detail(id ?? -1, isCustom),
    queryFn: () =>
      api.get<ExerciseTemplate>(isCustom ? `/custom-exercise-templates/${id}` : `/exercise-templates/${id}`),
    enabled: id !== undefined,
  })
}

export interface ExerciseHistoryItem {
  workout_id: number
  date: string
  notes: string | null
  sets: WorkoutSet[]
}

export function useExerciseHistory(ref: Partial<ExerciseRef> | undefined) {
  const { id, isCustom } = refParts(ref)
  const path = isCustom ? `/custom-exercise-templates/${id}/history` : `/exercise-templates/${id}/history`
  return useQuery({
    queryKey: exerciseTemplateKeys.history(id ?? -1, isCustom),
    queryFn: () => api.get<{ total: number; items: ExerciseHistoryItem[] }>(path),
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
export function useExercisePlanPreview(ref: Partial<ExerciseRef> | undefined, params: PlanPreviewParams) {
  const { id, isCustom } = refParts(ref)
  const search = new URLSearchParams()
  search.set('warmup_sets', String(params.warmupSets))
  search.set('target_sets', String(params.targetSets))
  search.set('drop_sets', String(params.dropSets))
  if (params.targetReps) search.set('target_reps', params.targetReps)
  const path = isCustom
    ? `/custom-exercise-templates/${id}/plan-preview`
    : `/exercise-templates/${id}/plan-preview`
  return useQuery({
    queryKey: exerciseTemplateKeys.planPreview(id ?? -1, isCustom, params),
    queryFn: () => api.get<PlanPreviewSet[]>(`${path}?${search}`),
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

/** Always creates a *custom* exercise -- a dataset-sourced one only ever comes from the seed
 * script, never from this user-facing endpoint. See CustomExerciseTemplate. */
export function useCreateExerciseTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: {
      name: string
      muscle_group_id: number
      equipment?: Equipment
      tracking_type?: TrackingType
      notes?: string
    }) => api.post<ExerciseTemplate>('/custom-exercise-templates', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: exerciseTemplateKeys.all }),
  })
}

/** For a catalog exercise this only ever accepts `notes` (everything else about it is shared,
 * common data -- see routes/exercise_templates.py); a custom one accepts any of its own fields. */
export function useUpdateExerciseTemplate(ref: Partial<ExerciseRef>) {
  const { id, isCustom } = refParts(ref)
  const qc = useQueryClient()
  const path = isCustom ? `/custom-exercise-templates/${id}` : `/exercise-templates/${id}`
  return useMutation({
    mutationFn: (data: Partial<ExerciseTemplate>) => api.patch<ExerciseTemplate>(path, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: exerciseTemplateKeys.all })
      qc.invalidateQueries({ queryKey: exerciseTemplateKeys.detail(id ?? -1, isCustom) })
    },
  })
}

/** Only ever a custom exercise -- a catalog one can't be deleted through the API at all (shared,
 * common data; see routes/exercise_templates.py's DELETE route, which always refuses). */
export function useDeleteExerciseTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.delete(`/custom-exercise-templates/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: exerciseTemplateKeys.all }),
  })
}
