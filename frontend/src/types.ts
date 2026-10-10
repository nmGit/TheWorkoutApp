import type { Muscle } from '@abdofallah/musclemap-js'

export type WeightUnit = 'lbs' | 'kg'
export type DistanceUnit = 'mi' | 'km'
export type Theme = 'system' | 'light' | 'dark' | 'green' | 'pink'
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
  /** Small diagram standing in for the group, or null when there isn't one. */
  image_url: string | null
}

export interface LastPerformed {
  date: string
  summary: string
}

/** A muscle as its source dataset names it, plus a highlighted-body diagram
 * when RepDB happens to have one under the same name. */
export interface MuscleSwatch {
  /** Stable key (e.g. "pectoralis_major") used to filter the exercise library. */
  slug: string
  name: string
  image_url: string | null
  /** The body-diagram regions this muscle lights up (from the backend mapping). */
  regions: Muscle[]
}

/** A specific muscle that some exercise in a muscle group works. */
export interface MuscleOption {
  slug: string
  name: string
  image_url: string | null
}

/** An exercise, the abstract idea of it -- name, muscle group, equipment,
 * tracking type, description/instructions/notes. Dataset-sourced templates
 * (`is_custom: false`) additionally carry image/instructions metadata;
 * custom ones (`is_custom: true`) don't, since that's the only real
 * difference between the two. There is no separate per-user "Exercise"
 * entity -- a workout's logged sets and a saved routine's slots link
 * straight to this. */
export interface ExerciseTemplate {
  id: number
  external_id: string | null
  name: string
  category: string | null
  body_part: string | null
  /** This app's own fixed equipment vocabulary, used for filtering. */
  equipment: Equipment | null
  /** The dataset's original equipment wording, kept for display only. */
  equipment_raw: string | null
  target_muscle: string | null
  muscle_group: string | null
  muscle_group_id: number | null
  muscle_group_name: string | null
  tracking_type: TrackingType | null
  primary_muscles: MuscleSwatch[]
  secondary_muscles: MuscleSwatch[]
  instructions: string | null
  instruction_steps: string[]
  tips: string[]
  difficulty: string | null
  mechanic: string | null
  /** First image, for thumbnails. */
  image_url: string | null
  /** All images: two poses (start, peak) where RepDB covers the exercise, else at most one. */
  image_urls: string[]
  attribution: string | null
  notes: string | null
  is_custom: boolean
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
  rest_seconds: number | null
  /** Expected values for a set started from a template: ghost text until the set is completed. */
  planned_weight: number | null
  planned_weight_unit: WeightUnit | null
  planned_reps: number | null
  planned_duration_seconds: number | null
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

/** The muscles a workout or template works, rolled up from its exercises. Slugs
 * are canonical; groups are in the app's group order. */
/** Strength status of one muscle in one workout (see docs/source/features/strength_score.rst).
 * "scored": ratio is this workout's value against the muscle's moving average (1.0 = no change).
 * "no_baseline": worked, but not enough earlier workouts to compare with yet.
 * "pending": planned or skipped, with no completed set yet. */
export type StrengthStatus = 'scored' | 'no_baseline' | 'pending'

export interface MuscleStrength {
  status: StrengthStatus
  regions: Muscle[]
  ratio: number | null
  /** How much logged work the muscle's change rests on (higher is more evidence). */
  evidence?: number
}

export interface WorkoutStrength {
  /** Geometric mean of the scored muscles' ratios; null until some muscle has enough history. */
  score: number | null
  /** Keyed by canonical muscle slug. Muscles not listed have no data. */
  muscles: Record<string, MuscleStrength>
}

/** One completed workout's strength score. `score` is null during the warm-up period. */
export interface StrengthPoint extends WorkoutStrength {
  workout_id: number
  date: string
  template_id: number | null
}

export interface MuscleSummary {
  primary: string[]
  secondary: string[]
  groups: string[]
  /** Every region the workout's or template's muscles light up. */
  regions: Muscle[]
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
  muscles: MuscleSummary
}

export interface WorkoutSummary extends Omit<Workout, 'exercises'> {
  exercise_count: number
}

export interface TemplateExercise {
  id: number
  exercise_id: number
  exercise_name: string | null
  position: number
  /** Working sets a workout starts with. */
  target_sets: number | null
  warmup_sets: number
  drop_sets: number
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
  muscles: MuscleSummary
  exercises: TemplateExercise[]
}

export type ProgressionMethod = 'double' | 'linear' | 'off'
export type Experience = 'novice' | 'intermediate'

export interface UserSettings {
  weight_unit: WeightUnit
  distance_unit: DistanceUnit
  default_rest_seconds: number
  theme: Theme
  progression_method: ProgressionMethod
  experience: Experience
  load_step_lb: number
  load_step_kg: number
  default_rep_range: string
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
