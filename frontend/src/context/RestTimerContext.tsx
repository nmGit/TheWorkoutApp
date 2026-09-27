import { createContext, useContext, type ReactNode } from 'react'
import { useActiveWorkout } from '../api/workouts'
import { useRestTimer, type RestTimerState } from '../hooks/useRestTimer'

const RestTimerContext = createContext<RestTimerState | null>(null)

export function RestTimerProvider({ children }: { children: ReactNode }) {
  const { data: activeWorkout } = useActiveWorkout()
  const timer = useRestTimer(activeWorkout?.id ?? null)

  return <RestTimerContext.Provider value={timer}>{children}</RestTimerContext.Provider>
}

export function useGlobalRestTimer(): RestTimerState {
  const ctx = useContext(RestTimerContext)
  if (!ctx) throw new Error('useGlobalRestTimer must be used within RestTimerProvider')
  return ctx
}
