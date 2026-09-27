import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { BodyweightEntry, UserSettings } from '../types'

export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: () => api.get<UserSettings>('/settings'),
    staleTime: Infinity,
  })
}

export function useUpdateSettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<UserSettings>) => api.patch<UserSettings>('/settings', data),
    onSuccess: (data) => qc.setQueryData(['settings'], data),
  })
}

export function useBodyweightEntries() {
  return useQuery({
    queryKey: ['bodyweight'],
    queryFn: () => api.get<BodyweightEntry[]>('/bodyweight'),
  })
}

export function useUpsertBodyweight() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { weight: number; recorded_at?: string; unit?: string }) =>
      api.post<BodyweightEntry>('/bodyweight', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bodyweight'] })
      qc.invalidateQueries({ queryKey: ['bodyweight-stats'] })
    },
  })
}

export function useDeleteBodyweight() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.delete(`/bodyweight/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bodyweight'] })
      qc.invalidateQueries({ queryKey: ['bodyweight-stats'] })
    },
  })
}
