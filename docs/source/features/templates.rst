Workout templates
===================

A template (routine) is a saved shape for a workout: which exercises, in
what order, with target sets/reps/weight. Templates make starting a
workout a single tap instead of rebuilding the exercise list from scratch
every session.

Template list
--------------

.. image:: /_static/screenshots/templates.png
   :alt: The template list screen
   :width: 360px
   :align: center

``/templates`` shows all templates, user-orderable (drag to reorder,
persisted to ``display_order``), each card showing name and a compact list
of its exercises. Tapping a card's primary action starts a workout from it
immediately (``POST /api/workouts {template_id}``); tapping the card body
opens the editor.

Template editor
-----------------

.. image:: /_static/screenshots/template_editor.png
   :alt: The template editor, with per-exercise set counts and rep range
   :width: 360px
   :align: center

- Name (required) and notes (optional free text).
- Ordered list of exercises, each with:

  - **Warm-up / Sets / Drop** counters — how many sets of each kind the
    workout starts with. "Sets" (the working sets) is what progressive
    overload applies to; warm-ups and drops always just copy that same
    kind of set from last time, unchanged (see
    :doc:`progressive_overload`).
  - **Rep range**, a free-form string like ``8-12`` (a single number like
    ``10`` also works). This is the per-exercise override of the default
    rep range from Settings → Generated Workouts — the one place in the
    template editor that tweaks progressive overload for this exercise
    specifically. Left blank, the exercise uses the Settings default.
  - A live preview of each planned set, shown as ghost text rather than
    editable here — the template doesn't store weights or reps itself.
    It reflects what :doc:`progressive overload <progressive_overload>`
    would actually plan right now, with the same color and "P" badge
    cues used on the active workout screen, and updates immediately as
    you change the set counts or rep range above — so you can see the
    effect of a change before starting a workout, not just after.
  - The card's "⋯" menu includes pairing it with the next exercise into a
    :doc:`superset <supersets>` (shown by a blue bar along the left edge
    of both cards once paired) — forcing the two to the same working-set
    count.

- Reordering via drag handle; removing an exercise from the template does
  not touch any workout history that used it.
- "+ Add exercise" opens the same searchable exercise picker used in
  active workouts.
- No explicit save button — changes autosave (``PATCH`` on blur/reorder),
  consistent with the active-workout screen's autosave behavior and
  avoiding lost edits.
- Finishing a workout that came from a template, with its exercises still
  the same *set* but reordered, offers to apply that new order back to the
  template too (a confirm dialog — declining keeps the new order for just
  that one workout).

Creating a template from a past workout
------------------------------------------

From any completed workout's detail view, "Save as template" creates a
``WorkoutTemplate`` + ``TemplateExercise`` rows from that workout's
exercises, using the actual logged weight/reps of the last set of each
exercise as the target. This is the fastest path to a template for users
migrating from ad hoc logging (including the imported historical data —
see :doc:`../data_migration`), and mirrors Strong's "create routine from
workout" affordance. The new template's set count is the workout's total
set count for that exercise, undivided into warm-up/working/drop — it
doesn't look at which of the source sets were flagged as warm-ups or drops,
so everything becomes working sets (0 warm-ups, 0 drops) regardless. Split
them in the editor afterward if needed.

Starting a workout from a template
-------------------------------------

Covered in :doc:`workout_logging`; noted here for completeness: the
workout keeps a ``template_id`` reference for its lifetime (used to show
"Push Day" as a subtitle in history), but editing the template afterward
never retroactively changes past workouts, and deleting the template
leaves history intact with ``template_id`` set to null.
