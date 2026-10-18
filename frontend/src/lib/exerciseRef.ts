/** A reference to either a catalog exercise or the user's own custom one -- the two live in
 * separate databases now (see docs/data_model.rst "Database split"), so a bare id is ambiguous
 * on its own; exactly one of these two fields says which table it means. Mirrors the backend's
 * ExerciseReferenceMixin (WorkoutExercise/TemplateExercise) and the API's own request/response
 * shape for them. */
export interface ExerciseRef {
  exercise_id: number | null
  custom_exercise_id: number | null
}

/** The ref for a freshly-picked exercise (from the exercise library/picker, which returns an
 * ExerciseTemplate-shaped row with `is_custom` saying which table it's actually in). */
export function refForExercise(exercise: { id: number; is_custom: boolean }): ExerciseRef {
  return exercise.is_custom
    ? { exercise_id: null, custom_exercise_id: exercise.id }
    : { exercise_id: exercise.id, custom_exercise_id: null }
}

/** This ref's id and whether it's the custom one -- for building a request against whichever of
 * the two API paths actually has it (``/exercise-templates/:id/...`` vs.
 * ``/custom-exercise-templates/:id/...``, ``/exercises/:id/stats`` vs.
 * ``/custom-exercises/:id/stats``). `undefined` id means "nothing to look up yet" (mirrors the
 * existing `id: number | undefined` pattern these hooks used before the split). */
export function refParts(ref: Partial<ExerciseRef> | undefined): { id: number | undefined; isCustom: boolean } {
  if (ref?.custom_exercise_id != null) return { id: ref.custom_exercise_id, isCustom: true }
  return { id: ref?.exercise_id ?? undefined, isCustom: false }
}
