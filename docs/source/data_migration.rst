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
   recorded."`` (see the :ref:`model-workoutexercise` table).
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
  sets get no ``rest_seconds`` value (the global default in
  ``UserSettings`` applies until the lifter logs a real one going forward
  — see :doc:`features/rest_timers`).

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
   ``ExerciseTemplate`` row (see :ref:`data_migration:Exercise matching` below),
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
   and re-run ``seed_exercise_templates.py`` before importing again. Three
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
  recorded by Strong's own timer) are read but not persisted anywhere.
  ``WorkoutSet.rest_seconds`` exists now (see :doc:`features/rest_timers`)
  and could receive this real signal on a future import; not wired up
  here, to keep this import's scope to "get the set data in correctly."

Backfilling exercise templates for pre-existing exercises
------------------------------------------------------------

.. note::
   This section describes a step that has since been superseded: the
   separate ``Exercise``/``ExerciseTemplate`` split it backfilled was
   later merged into one table (see
   :ref:`data_migration:Merging Exercise into ExerciseTemplate` below),
   and ``backfill_exercise_templates.py`` no longer exists. Kept here as
   history — the matching work and its reasoning (below) directly fed
   into the later merge.

The ``ExerciseTemplate`` feature (see the :ref:`model-exercisetemplate`
table and :ref:`features/exercise_library:Exercise templates`) added
``Exercise.template_id`` as a nullable foreign key. Every exercise created
*after* that feature shipped always gets one — either a dataset template
picked in the exercise picker, or an auto-created custom template if
built from scratch (``app/routes/exercises.py:create_exercise``). The 72
exercises seeded before the feature existed don't: the migration that
added the column only adds it, it can't retroactively know which of the
1,324 dataset entries (if any) each name actually matches.
``backend/scripts/backfill_exercise_templates.py`` does that matching,
once, and is safe to re-run (it only touches exercises with
``template_id IS NULL``).

Matching approach: hand-reviewed, not automated
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Automated fuzzy name matching was tried first (token-overlap scoring
against the dataset's 1,324 names) and rejected as the actual matching
mechanism, though it's still useful as a first-pass candidate generator.
Two concrete failure modes made blind top-score matching unsafe for
something that changes what image and instructions a lifter sees:

- The dataset's naming is equipment-*prefixed* (``"barbell incline bench
  press"``) where this app's is equipment-*suffixed*
  (``"Incline Bench (Barbell)"``), and inconsistent about singular vs.
  plural muscle words (``"bicep"`` vs. ``"biceps"``) — both distort
  naive string-similarity scoring in ways that aren't obvious from the
  score alone.
- The single worst case found: ``"One Arm Row (Dumbbell)"`` fuzzy-matched
  highest against ``"dumbbell one arm upright row"`` — a real dataset
  exercise, equipment-correct, high similarity score — but a completely
  different movement (upright row vs. bent-over row) from what this
  app's exercise actually is. The correct match,
  ``"dumbbell one arm bent-over row"``, scored *lower*.

Given that, every one of the 72 was matched by hand, using the fuzzy
scorer's candidates as a starting point but verifying each one against
the dataset's actual instructions/equipment rather than trusting the
score. The result is committed as
``backend/scripts/seed_data/exercise_template_mapping.json`` — a
``{exercise name: dataset external_id (or null)}`` mapping, reviewed once
and re-run rather than re-derived, the same policy as
``seed_data/exercises.json``.

Exercises with no correct dataset match
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

8 of the 72 have no entry in the 1,324-exercise dataset that's actually
the same movement (checked directly, not just "nothing scored well"):
``Stretching`` (the dataset has no mobility/stretching category at all),
``Plank`` and ``Face Pull (Cable)`` (the exact movement isn't in the
dataset under any name — every "plank" entry adds a twist/incline/weight
qualifier that would make the shown instructions describe a different
exercise), ``Captain's Chair Knee Raise`` and ``Flat Knee Raise`` (no
apparatus/lying-variant match), ``Bulgarian Split Squat`` (no
rear-foot-elevated variant), and ``Rowing Machine``/``Treadmill Run``
(this dataset is almost entirely strength exercises — only 29 of 1,324
are cardio, and neither a rowing machine nor a running-specific treadmill
entry exists; the closest treadmill entry is a walking-specific incline
variant, used instead for ``Walking``). Each of these gets its own
auto-created custom ``ExerciseTemplate`` (``is_custom: true``), the same
fallback path a from-scratch custom exercise goes through — see
:ref:`features/exercise_library:Custom exercises`.

Equipment correction
~~~~~~~~~~~~~~~~~~~~~~~

While reviewing matches, ``Sumo Deadlift High Pull`` — seeded with
``equipment: "other"`` since the spreadsheet import had no equipment
signal for it — turned out to match the dataset's
``"kettlebell sumo high pull"`` closely enough (by instructions, not just
name) that its equipment is corrected to ``kettlebell`` at the same time,
the same kind of evidence-based correction as ``Goblet Squat``'s earlier
in this document.

Merging Exercise into ExerciseTemplate
------------------------------------------

The two-table design above — a personal ``Exercise`` row linked via a
nullable ``Exercise.template_id`` to an ``ExerciseTemplate`` row — had a
real bug baked into its shape: nothing prevented (or even detected) two
different ``Exercise`` rows pointing at the same template. That's exactly
what happened by mistake in ``exercise_template_mapping.json`` (both
``"Military Press"`` and a later Strong-import addition,
``"Strict Military Press (Barbell)"``, got mapped to the same dataset
entry, and separately ``"Tricep Extension"``/``"Tricep Extension
(Cable)"``), and it surfaced as a real user-facing bug: clicking a
template card in the catalog would sometimes open the *wrong* exercise's
history, because the endpoint resolving "which Exercise does this
template belong to" had two candidates and picked one arbitrarily. See
:doc:`review` for the incident.

The fix was structural, not just a data correction: ``ExerciseTemplate``
absorbed every field that used to live on ``Exercise``
(``muscle_group_id``, ``equipment``, ``tracking_type``, ``notes``), and
``WorkoutExercise``/``TemplateExercise`` were repointed to reference
``ExerciseTemplate.id`` directly. There's no longer a second row to
mis-link — a template *is* the exercise now.

Two fields didn't carry over as-is:

- ``equipment`` used to mean two different things on the two tables — this
  app's fixed enum on ``Exercise``, the dataset's own free-text wording on
  ``ExerciseTemplate``. The app's enum won the merged column (it's what
  filtering needs); the dataset's original wording is preserved under the
  new ``equipment_raw`` field rather than discarded.
- ``Exercise.default_rest_seconds`` was dropped entirely rather than
  merged — it turned out to have never been used in practice: 0 of the 73
  real exercises in production had one set, and it was always a
  manually-typed config value, never derived from actual rest behavior
  (see :ref:`data_migration:Known limitations (Strong import)` above,
  which discards exactly that signal on import). It's replaced by
  ``WorkoutSet.rest_seconds`` — see :doc:`features/rest_timers` for the
  new, per-set design.

Migration mechanics
~~~~~~~~~~~~~~~~~~~~~~

Done as two hand-authored Alembic migrations with a data script run
manually in between, rather than one migration with the FK retarget and
data rewrite combined — this project's established pattern (data
migrations are never embedded in Alembic files, e.g. the
``backfill_exercise_templates.py`` step above) extended to the FK-retarget
case too:

1. A migration adds the four new nullable columns to ``exercise_templates``
   and retargets ``workout_exercises.exercise_id``/
   ``template_exercises.exercise_id``'s foreign key to
   ``exercise_templates.id`` (SQLite ``batch_alter_table`` with an explicit
   ``copy_from`` table definition, needed because those original foreign
   keys were never named — see the migration file for why a plain
   ``drop_constraint`` by name doesn't work here). ``WorkoutSet.rest_seconds``
   is added in the same migration.
2. A standalone script copies every ``Exercise`` row's fields onto its
   already-linked template (every exercise already had a non-null
   ``template_id`` from the earlier backfill), and rewrites
   ``workout_exercises``/``template_exercises`` foreign key *values* from
   the old ``Exercise.id`` space to the matching ``ExerciseTemplate.id`` —
   as one atomic ``UPDATE`` with a correlated subquery against the
   still-intact ``exercises`` table, not a per-row loop. That distinction
   mattered in practice: ``Exercise.id`` and ``ExerciseTemplate.id`` are
   separate auto-increment sequences that share integer values (e.g.
   exercise ``#9`` and template ``#9`` are unrelated rows), so rewriting
   one exercise at a time can have an earlier rewrite's target collide
   with a later exercise's own old id and silently redirect that later
   exercise's history onto the wrong template. Caught in testing against a
   throwaway copy before it ever touched real data. Every dataset-only
   template (never linked to an ``Exercise``) gets the same
   ``muscle_group_id``/``equipment``/``tracking_type`` auto-derivation
   dataset-only templates get during seeding (see below).
3. A second migration drops the now-empty ``exercises`` table. Its
   ``downgrade()`` deliberately raises rather than pretending an automatic
   rollback could restore the dropped data — restoring from a
   pre-migration file backup is the actual recovery path.

``seed_exercise_templates.py`` was extended to do the same
auto-derivation for a fresh install (no historical ``Exercise`` rows to
copy from), then apply ``seed_data/exercises.json``'s hand-curated
overrides on top — folding in what ``seed_exercises.py`` (now deleted)
used to do, so a from-scratch setup doesn't regress in metadata quality
compared to what real usage had.

Adopting RepDB as a second exercise source
----------------------------------------------

The original dataset's images are small and grainy and its text is uneven,
so `RepDB <https://repdb.co>`_ (609 curated exercises: clean two-pose
illustrations, tips, difficulty, primary/secondary muscles, plus highlighted
muscle diagrams) was added as a second submodule,
``external/repdb-exercise-dataset``. The decision was to *augment* rather than
replace: RepDB's images/text/muscles are used wherever it covers an exercise,
and the original dataset stays as the fallback everywhere else — and, in
keeping with this project's habit of storing source data as given, each
source's fields are stored as that source provides them, with no translation
between RepDB's anatomical muscle names and the original dataset's coarser
terms. The only translation is the one needed to fill the app's own
fixed-vocabulary filter columns (``muscle_group_id``, ``equipment``,
``tracking_type``) when creating a *new* template from a RepDB entry.

Licensing shaped the mechanics: RepDB's free tier requires a visible
"Exercise data by RepDB (repdb.co)" link (Settings → *About & credits*, the
README, and each image's caption) and forbids redistributing the dataset or a
derived dataset — so it is a submodule, never committed here, and its paid-tier
animation previews are not used.

How existing exercises were matched to RepDB
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Same policy as the original template backfill: nothing that decides which
image a lifter sees is linked by fuzzy score. In priority order:

1. ``seed_data/repdb_mapping.json`` — 40 links and 15 explicit "checked, no
   equivalent" entries for the exercises actually in use (logged or in a
   routine), checked by hand against RepDB's name, equipment and
   instructions. Examples where wording differs: ``Stair Stepper`` →
   *Stair Climber*, ``Forearm Curl`` → *Barbell Wrist Curl*, ``lever chest
   press`` → *Machine Chest Press*. A null entry also blocks step 2, e.g.
   ``barbell hack squat`` is *not* RepDB's (machine) *Hack Squat*.
2. Exact **word-set** equality between names, only when unambiguous —
   101 more on the real database (e.g. ``dumbbell bent over row`` =
   *Bent-Over Dumbbell Row*). All 101 were read before applying.
3. Otherwise the RepDB entry becomes a new template (468 of them).

Each RepDB id can be claimed by at most one template — the same one-to-one
rule whose violation caused the earlier wrong-click bug. Near-matches (42, e.g.
RepDB's *Smith Machine Bench Press* vs. the original's ``smith bench press``)
are reported by the seed script but deliberately not auto-merged.

Mechanics and the bugs this surfaced
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A purely additive migration adds ``repdb_id`` (unique index), ``repdb_images``,
``primary_muscles``, ``tips``, ``difficulty``, ``mechanic`` and ``aliases``;
``seed_exercise_templates.py`` does the rest, re-runnable and with a
``--dry-run``. Two things came up in building it:

- **The previous seed script clobbered edits on re-run.** It re-applied every
  field to existing rows, so a second run would have renamed "Military Press"
  back to the dataset's wording and then created a duplicate through its
  name-matched curated pass — despite being documented as safe to re-run. The
  rewrite enforces one ownership rule: fields editable in the app (``name``,
  ``equipment``, ``tracking_type``, ``muscle_group_id``, ``notes``,
  ``is_custom``) are set only when seeding *creates* a row; re-runs refresh
  only dataset-owned fields. Covered by tests that fail if the old behavior
  returns.
- **Deleting a merged-away dataset template resurrects it.** The "Overhead
  Press (Barbell)" → "Military Press" merge first deleted the emptied row, and
  the rehearsal's dry-run showed the next seed recreating both it and its
  curated-list entry. The merge instead moves the history (and any routine
  slots) and returns the emptied row to being the dataset's own entry
  (*barbell seated overhead press*, genuinely a different exercise), and the
  curated entry was removed — the same fix as the earlier merges.

``aliases`` records the other names a merged exercise is known by, and
``import_strong_csv.py`` consults it, so a later Strong export that still says
"Overhead Press (Barbell)", "Strict Military Press (Barbell)" or "Tricep
Extension (Cable)" resolves to the surviving exercise instead of stopping with
"no existing exercise matches".

Everything was rehearsed on a copy of the real database first (migration,
merge, seed, a second seed run proven a no-op), then applied with a fresh
backup: workouts / workout blocks / sets unchanged, no dangling references,
no duplicate RepDB ids, and the only pre-existing row whose app-owned fields
changed was the intentional reset of the merged-away template.
