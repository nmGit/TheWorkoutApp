import { useQuery } from '@tanstack/react-query'
import { api } from './client'
import type { ExerciseTemplate } from '../types'

export const exerciseTemplateKeys = {
  all: ['exercise-templates'] as const,
  list: (params: { q?: string; bodyPart?: string; equipment?: string; limit?: number; offset?: number }) =>
    ['exercise-templates', 'list', params] as const,
  detail: (id: number) => ['exercise-templates', 'detail', id] as const,
  facets: ['exercise-templates', 'facets'] as const,
}

export interface ExerciseTemplateListResult {
  total: number
  items: ExerciseTemplate[]
}

export function useExerciseTemplates(
  params: { q?: string; bodyPart?: string; equipment?: string; limit?: number; offset?: number } = {},
) {
  const search = new URLSearchParams()
  if (params.q) search.set('q', params.q)
  if (params.bodyPart) search.set('body_part', params.bodyPart)
  if (params.equipment) search.set('equipment', params.equipment)
  search.set('limit', String(params.limit ?? 30))
  search.set('offset', String(params.offset ?? 0))

  return useQuery({
    queryKey: exerciseTemplateKeys.list(params),
    queryFn: () => api.get<ExerciseTemplateListResult>(`/exercise-templates?${search.toString()}`),
  })
}

export function useExerciseTemplate(id: number | undefined) {
  return useQuery({
    queryKey: exerciseTemplateKeys.detail(id ?? -1),
    queryFn: () => api.get<ExerciseTemplate>(`/exercise-templates/${id}`),
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
