Data migration & ongoing import
==================================

There are two ways workout history gets into this database, covered in
turn below:

- :ref:`data_migration:Initial migration: legacy spreadsheet (one-time)` —
  the author's pre-existing history from a hand-maintained ``.ods``,
  imported once at setup.
- :ref:`data_migration:Ongoing updates: Strong app CSV export` — the
  ongoing way new workouts get in day to day: exporting a fresh CSV from
  the Strong app and re-running an importer that's safe to run repeatedly.

Initial migration: legacy spreadsheet (one-time)
----------------------------------------------------

The author's pre-existing workout history (October 2021 onward) lived in
``Weightlifting.ods``, a hand-maintained spreadsheet, structurally similar
to a Strong CSV export pivoted wide. ``backend/scripts/import_ods.py``
converted it into the relational schema once, at initial setup. It has no
ongoing role now that :ref:`data_migration:Ongoing updates: Strong app CSV
export` covers the same history (and more precisely — see
:ref:`data_migration:Why the CSV superseded the spreadsheet`) plus
everything logged since; it's documented here for the historical record
and because its exercise-matching conventions (equipment parsing,
category corrections) carried forward into the CSV importer.

Source format
~~~~~~~~~~~~~~

- **Sheet1**, row 0: category headers (``Body``, ``Cardio``, ``Chest``,
  ``Back``, ``Shoulders``, ``Arms``, ``Core``, ``Legs``), sparsely filled
  (only set on each category's first column) — forward-filled to get a
  category per column.
- Row 1: exercise names per column, e.g. ``Bench Press``,
  ``Incline Bench (Dumbbell)``. A trailing ``(Equipment)`` suffix, when
  present, is the equipment type. Where absent, the importer falls back to
  common gym-equipment convention for well-known movements (e.g. plain
  ``Bench Press``/``Squat``/``Military Press`` → ``barbell``, ab/core
  bodyweight movements → ``bodyweight``, named cardio machines →
  ``machine``); genuinely ambiguous names default to ``other``. The full
  mapping is in ``backend/scripts/seed_data/exercises.json``, which is the
  actual seed data (hand-reviewed once, not regenerated on every run).
- Column 0, rows 2+: one row per workout date.
- Each remaining cell, when non-empty, holds a comma-separated list of set
  groups for that exercise on that date, in one of these forms (observed
  across all ~930 non-empty cells in the source file):

  .. list-table::
     :widths: 30 30 40
     :header-rows: 1

     * - Pattern
       - Example
       - Meaning
     * - ``{sets}×{reps} @ {weight}``
       - ``3×10 @ 105``
       - 3 identical sets of 10 reps at 105 lbs
     * - ``{sets}×{reps}``
       - ``3×10``
       - 3 sets, bodyweight (no weight recorded)
     * - ``{sets}×{seconds}s``
       - ``2×60s``
       - 2 sets, time-based (planks, holds)
     * - ``{n} min`` / ``{n} min, {mi} mi``
       - ``15 min, 0.86 mi``
       - Cardio duration, optionally with distance
     * - ``... @ {weight} drop``
       - ``1×5 @ 65 drop``
       - A drop set performed after the preceding group
     * - ``done``
       - ``done``
       - Exercise was performed; no set-level numbers were recorded

  A cell commonly contains several comma-separated groups representing
  different weights/reps used across the sets of that exercise that day,
  e.g. ``1×10 @ 105, 2×8 @ 105`` (one set of 10, then two sets of 8, same
  weight) or ``1×5 @ 95, 2×5 @ 65, 1×7 @ 65, 1×5 @ 65`` (a heavier top set
  followed by back-off sets).

Mapping to the schema
~~~~~~~~~~~~~~~~~~~~~~~~

For each source row (date) with at least one filled exercise cell:

1. Create one ``Workout`` with ``name = "Workout"``, ``started_at`` =
   ``completed_at`` = that date at midnight local time (the source has no
   time-of-day or duration data), ``template_id = null``.
2. For each filled column (exercise) in that row, in column order: create
   one ``WorkoutExercise`` linking to the ``Exercise`` seeded from that
   column (matched by name — the seed step runs first and creates one
   ``Exercise`` per distinct column, categorized by its forward-filled
   ``MuscleGroup``, with ``tracking_type`` inferred per
   :ref:`data_migration:Tracking-type inference`).
3. Parse the cell's comma-separated groups into ``WorkoutSet`` rows in
   order (``position`` = index within the cell), expanding ``{sets}×...``
   into that many individual rows (a repeated cross-set weight is *not*
   collapsed into one row with a "sets" count, since ``WorkoutSet`` models
   one physical set each, consistent with how sets are logged
   going forward).
4. A ``drop`` suffix sets ``is_dropset = true`` on that group's row(s).
5. A bare ``done`` cell creates the ``WorkoutExercise`` with no
   ``WorkoutSet`` rows and ``notes = "Imported: marked done, no set data
   recorded."`` (see the ``WorkoutExercise`` table in :doc:`data_model`).
6. All imported weights are assumed **lbs** (``weight_unit = "lbs"``) —
   consistent with the numeric ranges in the source (45-225 range typical
   of plate-loaded lbs, not kg) — and all imported distances assumed
   **miles**.

Category correction: ``Body``/``Deadlift``/``Kettlebell Swing``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The source sheet's category row (row 0) is sparse — only set on a
category's first column — and forward-filled to cover the rest of that
category's columns (see :ref:`data_migration:Source format`). Three
columns (``Deadlift (Barbell)``, ``Kettlebell Swing``, ``Sumo Deadlift
High Pull``) sit immediately after the lone ``Body`` header (over
``Stretching``) with blank category cells of their own, so a literal
forward-fill would categorize them as ``Body`` — which doesn't reflect
what they train and isn't a usable muscle group for three compound
barbell/kettlebell lifts. The importer special-cases these three by name
to their actual primary movement pattern instead of trusting the
forward-fill:

.. list-table::
   :widths: 40 30
   :header-rows: 1

   * - Column
     - Assigned MuscleGroup
   * - Deadlift (Barbell)
     - Back
   * - Kettlebell Swing
     - Full Body
   * - Sumo Deadlift High Pull
     - Full Body
   * - Stretching (the actual ``Body``-category column)
     - Mobility

This is the one place the importer overrides the literal source structure
rather than translating it as-is, and is called out here because it's a
judgment call, not a mechanical mapping.

Tracking-type inference
~~~~~~~~~~~~~~~~~~~~~~~~~~

Applied once per exercise column when seeding, using the column's
category and the shape of its non-empty cells:

- Category ``Cardio`` → ``cardio``.
- Cells matching only the ``{n} min`` pattern (no ``×``) anywhere in the
  column → ``time`` (e.g. ``Stretching``, ``Plank``).
- Cells matching ``{sets}×{reps}s`` (explicit trailing ``s``) → ``time``.
- Column has at least one cell with an ``@ {weight}`` group → ``weight_reps``.
- Otherwise (only bare ``{sets}×{reps}``, no weight ever recorded) →
  ``bodyweight_reps``.

This mechanical rule mis-tags an exercise if its history contains even one
occasional weighted set (e.g. a weighted-vest push-up session) — it would
otherwise classify the whole column as ``weight_reps``. ``Push Up`` and
``Chest Dip`` hit exactly this case and are corrected to
``bodyweight_reps`` by hand in ``exercises.json`` (an added-weight set is
still representable there — see :ref:`data_model:Set tracking types` — so
no history is lost by the correction). Reviewed once at seed time, not
re-derived automatically; a newly-added exercise with the same pattern
would need the same manual check.

Idempotency & running the import
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``python backend/scripts/import_ods.py <path-to-ods>`` is safe to re-run
against an empty database only — it refuses to run (non-zero exit, no
writes) if any ``Workout`` rows already exist, so it can't silently
double-import. It was a one-time setup step, not an ongoing sync — see
:ref:`data_migration:Ongoing updates: Strong app CSV export` for how new
workouts actually get added now.

Known limitations
~~~~~~~~~~~~~~~~~~~~

- No time-of-day or workout duration in the source, so imported workouts
  all show midnight start times and no computed duration — cosmetic only,
  doesn't affect analytics (which key off date, not time).
- Ambiguous bare ``{sets}×{reps}`` cells in strength-looking columns
  (e.g., an occasional unweighted set logged for a normally-weighted
  exercise) import as reps with a null weight on that specific
  ``WorkoutSet`` rather than being dropped — correct per-set, but such an
  exercise's column-level ``tracking_type`` is still ``weight_reps`` since
  most of its history has weights.
- Rest times are not present in the source and are not inferred; imported
  exercises get no ``default_rest_seconds`` override (global default
  applies going forward).

Ongoing updates: Strong app CSV export
------------------------------------------

The author actually logs workouts in the `Strong
<https://www.strong.app/>`_ app day to day (this project's whole
:ref:`overview:Primary reference: Strong` is not a coincidence). Strong's
own CSV export is how new workouts get into this database now — export
from Strong, run ``python backend/scripts/import_strong_csv.py
<path-to-csv>``. Unlike the spreadsheet importer, **this one is meant to
be run repeatedly**: each run only imports workouts whose date isn't
already in the database, so re-running it after a few more logged
sessions in Strong picks up just the new ones.

CSV source format
~~~~~~~~~~~~~~~~~~~~

Strong exports one row per set (not one cell per exercise like the
spreadsheet), semicolon-delimited, with a fixed column set: ``Workout #``,
``Date`` (full timestamp), ``Workout Name``, ``Duration (sec)``,
``Exercise Name``, ``Set Order``, ``Weight (kg)``, ``Reps``, ``RPE``,
``Distance (meters)``, ``Seconds``, ``Notes``, ``Workout Notes``. This is
substantially richer than the spreadsheet: real timestamps and workout
duration (not just a date), weight already in kg as a precise float,
explicit RPE, and a few special ``Set Order`` values instead of
free-text cells:

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - ``Set Order``
     - Meaning
   * - ``1``, ``2``, ``3``, …
     - A regular working set, in order.
   * - ``D``
     - A drop set performed immediately after the preceding set(s) →
       ``is_dropset = true``.
   * - ``Rest Timer``
     - Not a set — the actual rest duration Strong's timer recorded
       between sets, in the ``Seconds`` column. Not imported as a
       ``WorkoutSet`` (see :ref:`data_migration:Known limitations
       (Strong import)`).
   * - ``Note``
     - Not a set — carries a per-exercise note in the ``Notes`` column,
       imported as that ``WorkoutExercise.notes``.

Mapping to the schema (Strong CSV)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For each ``Workout #`` group (all its rows share one timestamp):

1. Skip the whole workout if a completed ``Workout`` already exists with
   the same date (see :ref:`data_migration:Known limitations (Strong
   import)` for the one sharp edge in this rule).
2. Otherwise create one ``Workout`` with the CSV's real ``Workout Name``
   and ``started_at``, ``completed_at = started_at + Duration``, and
   ``notes`` from the CSV's ``Workout Notes`` column. This is a real
   improvement over the spreadsheet import, which had none of these.
3. For each exercise, in first-appearance order, resolve it to an
   ``Exercise`` row (see :ref:`data_migration:Exercise matching` below),
   then create ``WorkoutSet`` rows in row order (skipping ``Rest Timer``
   and ``Note`` rows) with ``weight_unit = "kg"`` — stored exactly as
   Strong exports it, not converted to lbs, per the per-entry-unit
   business rule in :doc:`data_model`; the app converts for display same
   as it would for any other unit mismatch.

Exercise matching
~~~~~~~~~~~~~~~~~~~~

Strong's exercise names don't line up 1:1 with the names seeded from the
spreadsheet (different capitalization/punctuation conventions, and Strong
is often more specific about equipment). Matching, in order:

1. **Exact name match** (case-insensitive).
2. **Normalized base-name match** — strip the trailing ``(Equipment)``
   suffix and non-alphanumeric characters from both sides (so ``V Up``
   matches the seeded ``V-Up``, ``Squat (Barbell)`` matches ``Squat``).
   If exactly one existing exercise shares that normalized base name, use
   it — and if Strong's equipment suffix disagrees with that exercise's
   stored ``equipment``, **update it to Strong's value**, since an actual
   logged set is more trustworthy than the spreadsheet importer's
   guess. This caught a real error: ``Goblet Squat`` had been guessed as
   ``dumbbell`` (a reasonable default) but the author actually trains it
   with a kettlebell — Strong's export corrected it automatically on
   first import.
3. **No match** → the importer refuses (raises, no partial write) rather
   than guessing a muscle group for a name it's never seen. The fix is to
   hand-add an entry to ``exercises.json`` (same "reviewed once" policy as
   the rest of the seed data — see :ref:`data_migration:Source format`)
   and re-run ``seed_exercises.py`` before importing again. Three
   exercises needed this on the first Strong import: ``Seated Palms Up
   Wrist Curl (Dumbbell)``, ``Strict Military Press (Barbell)``, and
   ``Triceps Pushdown (Cable - Straight Bar)`` — none of which appeared
   anywhere in the original spreadsheet.

Why the CSV superseded the spreadsheet
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first Strong export pulled was a full history back to the same
2021-10-11 start date as the spreadsheet, confirmed to be a strict
superset (every date already in the database from the spreadsheet import
was present in the CSV too) plus real timestamps, duration, RPE, and
explicit drop-set markers the spreadsheet never had. Practically, this
means the spreadsheet importer is fully retired: the CSV is both more
accurate and the format the author will keep exporting going forward, so
it's the one true ongoing import path now.

Backfilling names/timestamps for spreadsheet-era workouts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The 201 workouts originally imported by the spreadsheet importer kept
their spreadsheet-era limitations even after the Strong CSV importer
existed — generic ``name = "Workout"`` and a midnight ``started_at`` with
no real duration — since ``import_strong_csv.py`` only ever *adds* new
workouts, it doesn't touch ones that already exist. Once the CSV is
confirmed to be a full-history superset (see above), those two fields can
be safely backfilled from it: ``backend/scripts/backfill_workout_names.py
<path-to-csv>`` matches every existing completed ``Workout`` to its CSV
row by date (the same matching rule the importer itself uses) and updates
``name``, ``started_at``, and ``completed_at`` to the real values.

Deliberately narrow: it never touches ``WorkoutExercise`` or
``WorkoutSet`` rows, so it can't overwrite a set edited by hand through
the app after the original import — only the three workout-level fields
the spreadsheet import could never have gotten right in the first place.
Safe to re-run (a workout already matching its CSV values is left alone).
A workout with no same-date CSV entry (e.g. one created directly through
the app, like a manual test) is left completely untouched rather than
guessed at.

Known limitations (Strong import)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **The skip-if-date-exists rule assumes one workout per day.** It was
  briefly wrong in practice: a workout manually created through the app's
  own UI on the same calendar date as a real Strong session (an empty
  "Test" workout created while trying out the active-workout screen)
  blocked that day's real Strong data from importing, since the importer
  saw *a* workout on that date and assumed it was already covered. The
  fix at the time was manual (delete the stray manual workout, re-run the
  import) rather than a schema change, since a same-day collision between
  a manually-created workout and a real Strong session is expected to be
  rare. If it stops being rare, the fix would be matching on something
  more specific than date (e.g. exact timestamp) rather than adding
  multi-workout-per-day handling to the skip rule.
- ``Rest Timer`` rows (the *actual* rest duration taken between sets,
  recorded by Strong's own timer) are read but not persisted anywhere —
  there's no per-set "rest taken" field in the schema, only
  ``Exercise.default_rest_seconds`` as a forward-looking target. This is
  real, useful signal about what rest periods this lifter actually uses
  that the import currently discards; wiring it up (e.g., seeding
  ``default_rest_seconds`` from the median observed rest time per
  exercise) is a reasonable future improvement, not done here to keep
  this import's scope to "get the set data in correctly."
