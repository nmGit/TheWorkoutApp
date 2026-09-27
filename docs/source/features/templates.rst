Workout templates
===================

A template (routine) is a saved shape for a workout: which exercises, in
what order, with target sets/reps/weight. Templates make starting a
workout a single tap instead of rebuilding the exercise list from scratch
every session.

Template list
--------------

``/templates`` shows all templates, user-orderable (drag to reorder,
persisted to ``display_order``), each card showing name and a compact list
of its exercises. Tapping a card's primary action starts a workout from it
immediately (``POST /api/workouts {template_id}``); tapping the card body
opens the editor.

Template editor
-----------------

- Name (required) and notes (optional free text).
- Ordered list of exercises, each with: target sets (int), target reps
  (free-form string, so ``8-12`` ranges are valid, not just a fixed
  number), optional target weight.
- Reordering via drag handle; removing an exercise from the template does
  not touch any workout history that used it.
- "+ Add exercise" opens the same searchable exercise picker used in
  active workouts.
- No explicit save button — changes autosave (``PATCH`` on blur/reorder),
  consistent with the active-workout screen's autosave behavior and
  avoiding lost edits.

Creating a template from a past workout
------------------------------------------

From any completed workout's detail view, "Save as template" creates a
``WorkoutTemplate`` + ``TemplateExercise`` rows from that workout's
exercises, using the actual logged weight/reps of the last set of each
exercise as the target. This is the fastest path to a template for users
migrating from ad hoc logging (including the imported historical data —
see :doc:`../data_migration`), and mirrors Strong's "create routine from
workout" affordance.

Starting a workout from a template
-------------------------------------

Covered in :doc:`workout_logging`; noted here for completeness: the
workout keeps a ``template_id`` reference for its lifetime (used to show
"Push Day" as a subtitle in history), but editing the template afterward
never retroactively changes past workouts, and deleting the template
leaves history intact with ``template_id`` set to null.
