Workout tracking & logging
============================

This is the primary screen of the app, used *during* a workout, one-handed,
between sets.

Starting a workout
-------------------

A workout starts in one of two ways:

- **From a template** — ``POST /api/workouts`` with ``template_id``. The
  new workout is pre-populated with the template's exercises in order,
  each pre-filled with ``target_sets`` empty set rows (``completed:
  false``) using ``target_weight``/``target_reps`` as placeholder values.
- **Blank** — ``POST /api/workouts`` with no ``template_id``. Starts empty;
  exercises are added one at a time from the exercise picker.

Starting a workout while another is already active is rejected (see
:ref:`data_model:Business rules`); the UI instead navigates straight to the
existing active workout.

The active workout screen
---------------------------

Layout, top to bottom, matching Strong's proven structure:

1. **Header** — workout name (editable inline), elapsed time (live, ticking
   from ``started_at``), a "Finish" button.
2. **Exercise blocks**, in order. Each block has a small toolbar in its
   header — exercise name on the left, then a "view exercise page" button
   (jumps to :doc:`exercise_library`'s detail screen — chart, PRs, and
   full history — for that exercise) and a "Remove" button on the right —
   plus:

   - A row per set: set number, previous performance for that slot shown
     as greyed-out placeholder text (e.g. *"135 × 8"* from the last time
     this exercise was logged), weight input, reps input, a checkmark to
     mark the set ``completed``.
   - Warmup and drop-set toggles per set, in the row's "..." menu ("Mark
     as warmup" / "Mark as drop set", tucked away to keep the row compact on
     a phone). A marked set shows a small ``W`` or ``D`` badge under its set
     number. The two are mutually exclusive — marking one clears the other —
     and "+ Add set" never copies the flag, so a set added after a drop set
     is a regular set.
   - "+ Add set" appends a set, pre-filled by copying the previous set's
     values (fast repeat-set entry, the single most common action in a
     workout).

   The same header toolbar (view-exercise button included) appears on a
   completed workout's exercise blocks too — see
   :ref:`features/workout_logging:Editing past workouts`.

3. **"+ Add exercise"** at the bottom, opens the exercise picker
   (searchable, grouped by muscle group, recent/frequent exercises
   surfaced first).

Marking a set's checkmark (``completed: true``) is the single action that:

- Persists the set via ``PATCH /api/sets/:id``.
- Starts the rest timer (see :doc:`rest_timers`) from that set's rest
  field — or its ghost text if it's empty, which then fills the field in.
- Advances focus to the next set's weight input, or reveals "+ Add set" if
  it was the last one.

Finishing a workout
---------------------

"Finish" sets ``completed_at``. Any sets still ``completed: false`` are
dropped (they were never performed — this matters for templates that
over-provision optional sets). The user lands on the workout's read-only
summary (same layout as :doc:`history_and_analytics`'s detail view) which
highlights any new personal records set during the session.

Discarding a workout (abandoning it entirely, e.g. started by mistake) is
available from the header overflow menu and deletes the workout row and
its exercises/sets.

Editing past workouts
-----------------------

A completed workout's detail view is editable in place (fix a typo'd
weight after the fact) — the same set-row components as the active screen,
without the rest timer wiring. There is no separate "edit mode": any
completed workout can always be amended.
