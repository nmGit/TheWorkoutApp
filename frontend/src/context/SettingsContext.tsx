import { createContext, useContext, useEffect, type ReactNode } from 'react'
import { useSettings } from '../api/settings'
import type { UserSettings } from '../types'

const DEFAULT_SETTINGS: UserSettings = {
  weight_unit: 'lbs',
  distance_unit: 'mi',
  default_rest_seconds: 90,
  theme: 'system',
  progression_method: 'double',
  experience: 'intermediate',
  load_step_lb: 5,
  load_step_kg: 2.5,
  default_rep_range: '8-12',
}

const SettingsContext = createContext<UserSettings>(DEFAULT_SETTINGS)

export function SettingsProvider({ children }: { children: ReactNode }) {
  const { data } = useSettings()
  const settings = data ?? DEFAULT_SETTINGS

  useEffect(() => {
    const root = document.documentElement
    if (settings.theme === 'system') {
      root.removeAttribute('data-theme')
    } else {
      root.setAttribute('data-theme', settings.theme)
    }
  }, [settings.theme])

  return <SettingsContext.Provider value={settings}>{children}</SettingsContext.Provider>
}

export function useAppSettings(): UserSettings {
  return useContext(SettingsContext)
}
