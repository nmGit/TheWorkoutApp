export type WeightUnit = 'lbs' | 'kg'
export type DistanceUnit = 'mi' | 'km'
export type Theme = 'system' | 'light' | 'dark'
export type Equipment =
  | 'barbell'
  | 'dumbbell'
  | 'machine'
  | 'cable'
  | 'bodyweight'
  | 'kettlebell'
  | 'other'
export type TrackingType = 'weight_reps' | 'bodyweight_reps' | 'time' | 'cardio'

export interface MuscleGroup {
  id: number
  name: string
  display_order: number
}

export interface LastPerformed {
  date: string
  summary: string
}

export interface Exercise {
  id: number
  name: string
  muscle_group_id: number
  muscle_group_name: string | null
  equipment: Equipment
  tracking_type: TrackingType
  is_custom: boolean
  default_rest_seconds: number | null
  notes: string | null
  last_performed?: LastPerformed | null
}

export interface WorkoutSet {
  id: number
  position: number
  weight: number | null
  weight_unit: WeightUnit | null
  reps: number | null
  duration_seconds: number | null
  distance_meters: number | null
  is_warmup: boolean
  is_dropset: boolean
  rpe: number | null
  completed: boolean
}

export interface WorkoutExercise {
  id: number
  exercise_id: number
  exercise_name: string | null
  tracking_type: TrackingType | null
  position: number
  notes: string | null
  sets: WorkoutSet[]
}

export interface Workout {
  id: number
  name: string
  template_id: number | null
  template_name: string | null
  started_at: string
  completed_at: string | null
  notes: string | null
  body_weight: number | null
  is_active: boolean
  exercises: WorkoutExercise[]
}

export interface WorkoutSummary extends Omit<Workout, 'exercises'> {
  exercise_count: number
}

export interface TemplateExercise {
  id: number
  exercise_id: number
  exercise_name: string | null
  position: number
  target_sets: number | null
  target_reps: string | null
  target_weight: number | null
}

export interface WorkoutTemplate {
  id: number
  name: string
  notes: string | null
  display_order: number
  created_at: string
  updated_at: string
  exercises: TemplateExercise[]
}

export interface UserSettings {
  weight_unit: WeightUnit
  distance_unit: DistanceUnit
  default_rest_seconds: number
  theme: Theme
}

export interface BodyweightEntry {
  id: number
  recorded_at: string
  weight: number
  unit: WeightUnit
}

export interface StatsPoint {
  date: string
  value: number
  workout_id: number
}

export interface PersonalRecord {
  value: number
  date: string
  workout_id: number
}

export interface ExerciseStats {
  exercise_id: number
  metric: string
  series: StatsPoint[]
  personal_records: Record<string, PersonalRecord | null>
}

export interface RecentPr {
  exercise_id: number
  exercise_name: string
  metric: string
  value: number
  date: string
  workout_id: number
}

export interface DashboardStats {
  active_workout_id: number | null
  current_streak_weeks: number
  recent_prs: RecentPr[]
}
