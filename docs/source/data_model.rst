Data model
==========

The schema is relational (SQLAlchemy models, Alembic-versioned) so that
cross-exercise analytical queries — "every logged weight for Bench Press,
in order" — are plain joins, not application-level scans of nested
documents.

Entity-relationship overview
-----------------------------

.. code-block:: text

   MuscleGroup 1───* ExerciseTemplate 1───* TemplateExercise *───1 WorkoutTemplate
                                    │                                   │
                                    │                                   │ 1
                                    │                                   │
                                    │                                   * (optional, workout.template_id)
                                    │                                   │
                                    │                             WorkoutExercise *───────────────────────1 Workout
                                    │ 1                                 │ 1
                                    │                                   │
                                    *                                   *
                              WorkoutExercise                       WorkoutSet

   BodyweightEntry            (standalone, date + weight)
   UserSettings                (singleton row)

``ExerciseTemplate`` is the sole "what is this exercise" concept — name,
muscle group, equipment, tracking type, description/instructions/notes.
There is no separate per-user "Exercise" entity: a saved routine's slot
(``TemplateExercise``) and a workout's logged block (``WorkoutExercise``)
both link straight to it. This used to be two tables (a personal
``Exercise`` linked via a nullable ``template_id`` to a dataset/custom
``ExerciseTemplate``); they were merged after that nullable link let two
different exercises collide onto one template (see :doc:`review` for the
incident and :doc:`data_migration` for the merge itself). Dataset-sourced
templates (``is_custom: false``) additionally carry image/instructions
metadata from the bundled dataset submodules (RepDB and/or the original
exercises-dataset); custom ones
(``is_custom: true``) don't — that's the only real difference between the
two, everything else about them (filtering, editing, logging, stats) is
symmetric.

Core tables
-----------

.. _model-musclegroup:

``MuscleGroup``
~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Column
     - Type
     - Notes
   * - id
     - PK
     -
   * - name
     - string, unique
     - e.g. ``Chest``, ``Back``, ``Legs``, ``Shoulders``, ``Arms``,
       ``Core``, ``Cardio``, ``Full Body``, ``Mobility``
   * - display_order
     - int
     - Controls ordering in exercise picker

.. _model-exercisetemplate:

``ExerciseTemplate``
~~~~~~~~~~~~~~~~~~~~~

An exercise, the abstract idea of it — sourced from the bundled dataset
submodules (RepDB at ``external/repdb-exercise-dataset`` and the original
``external/exercises-dataset``, both imported by
``scripts/seed_exercise_templates.py``) or authored by a user from scratch.
A template can carry both sources' data: each source's own fields are stored
exactly as that source provides them, RepDB's images/text/muscles are
preferred wherever present, and the original's are the fallback. The
app-owned fields (``name``, ``equipment``, ``tracking_type``,
``muscle_group_id``, ``notes``, ``is_custom``) are set by seeding only when it
creates the row, never refreshed on a re-run, so edits made in the app
survive. See :doc:`features/exercise_library` for how these surface in the UI.

.. list-table::
   :widths: 22 22 56
   :header-rows: 1

   * - Column
     - Type
     - Notes
   * - id
     - PK
     -
   * - external_id
     - string, unique, nullable
     - The *original* dataset's own id (e.g. ``"0001"``); null for custom
       templates and for templates that came from RepDB.
   * - repdb_id
     - string(64), unique, nullable
     - RepDB's id (a slug like ``bench-press``); set on every template RepDB
       covers — whether it was created from RepDB or an existing template was
       matched to it (see :doc:`data_migration`).
   * - name
     - string
     - e.g. ``Bench Press``, ``Incline Bench (Dumbbell)``
   * - muscle_group_id
     - FK -> MuscleGroup, nullable
     - This app's own fixed muscle group, used for filtering. Nullable at
       the DB level (a handful of dataset ``body_part`` values have no
       clean mapping), enforced non-null at the API layer for new/edited
       templates.
   * - equipment
     - enum, nullable
     - This app's own fixed vocabulary — ``barbell`` / ``dumbbell`` /
       ``machine`` / ``cable`` / ``bodyweight`` / ``kettlebell`` /
       ``other`` — used for filtering. Nullable for the same reason as
       ``muscle_group_id``.
   * - equipment_raw
     - string, nullable
     - The dataset's own original equipment wording (e.g.
       ``leverage machine``), kept for display/reference only; null for
       custom templates, which never had dataset wording to begin with.
   * - tracking_type
     - enum, nullable
     - ``weight_reps`` / ``bodyweight_reps`` / ``time`` / ``cardio``. Drives
       which input fields the logging UI shows (see
       :ref:`data_model:Set tracking types`).
   * - notes
     - text, nullable
     - Free-text (form cues, etc.)
   * - category / body_part / target_muscle / muscle_group
     - string, nullable
     - The dataset's own vocabulary/classification (e.g. ``body_part:
       upper legs``) — display/reference only, never used for filtering.
       Null for custom templates.
   * - primary_muscles / secondary_muscles
     - JSON list of strings, nullable
     - Muscles worked, exactly as the source dataset names them — RepDB's
       anatomical slugs (``pectoralis_major``) or the original dataset's
       terms (``pectorals``). Not translated between vocabularies; the UI
       shows a muscle diagram only where RepDB happens to ship one under the
       same name.
   * - instructions
     - text, nullable
     - Full English instructions as a single paragraph.
   * - instruction_steps
     - JSON list of strings, nullable
     - Same instructions split into ordered steps; only English is
       imported even though the dataset ships 10 languages.
   * - tips / difficulty / mechanic
     - JSON list / string / string, nullable
     - RepDB-only: form cues, ``beginner``/``intermediate``/``advanced``,
       ``compound``/``isolation``.
   * - repdb_images
     - JSON list of strings, nullable
     - RepDB image paths relative to its checkout: ``[start, peak]`` (two
       poses) or ``[main]``. When set these win over ``image_path``; served
       via ``GET /api/exercise-templates/<id>/image[/<n>]``.
   * - image_path
     - string, nullable
     - The original dataset's single image, relative to its checkout (e.g.
       ``images/0001-2gPfomN.jpg``); the fallback when ``repdb_images`` is
       empty.
   * - aliases
     - JSON list of strings, nullable
     - Other names this exercise is known by — e.g. the Strong app's wording
       for an exercise that was merged into this one — consulted by
       ``import_strong_csv.py`` so a merged-away name still resolves.
   * - attribution
     - string, nullable
     - The notice the image's license requires, matching whichever source
       the shown image/text came from — ``© Gym visual — https://gymvisual.com/``
       or ``Exercise data by RepDB (repdb.co) — https://repdb.co`` — shown
       wherever the image is displayed.
   * - is_custom
     - bool
     - ``false`` for dataset-sourced templates, ``true`` for
       user-authored ones.
   * - created_at
     - datetime
     -

.. _model-workouttemplate:

``WorkoutTemplate``
~~~~~~~~~~~~~~~~~~~~

A saved, reusable shape for a workout ("routine" in Strong's terms).

.. list-table::
   :widths: 22 22 56
   :header-rows: 1

   * - Column
     - Type
     - Notes
   * - id
     - PK
     -
   * - name
     - string
     - e.g. ``Push Day``
   * - notes
     - text, nullable
     -
   * - display_order
     - int
     - User-controlled ordering in the template list
   * - created_at / updated_at
     - datetime
     -

.. _model-templateexercise:

``TemplateExercise``
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 22 22 56
   :header-rows: 1

   * - Column
     - Type
     - Notes
   * - id
     - PK
     -
   * - template_id
     - FK -> WorkoutTemplate
     - Cascade delete with template
   * - exercise_id
     - FK -> ExerciseTemplate
     -
   * - position
     - int
     - Order within the template
   * - target_sets
     - int, nullable
     -
   * - target_reps
     - string, nullable
     - Free-form to allow ranges like ``8-12``
   * - target_weight
     - decimal, nullable
     - Suggested starting weight, pre-fills the first set

.. _model-workout:

``Workout``
~~~~~~~~~~~

A single training session. **A workout with ``completed_at IS NULL`` is
the in-progress "active workout"; the API enforces at most one such row at
a time** (see :doc:`api/workouts`).

.. list-table::
   :widths: 22 22 56
   :header-rows: 1

   * - Column
     - Type
     - Notes
   * - id
     - PK
     -
   * - name
     - string
     - Defaults to the source template's name, or ``Workout`` if started
       blank; user-editable
   * - template_id
     - FK -> WorkoutTemplate, nullable
     - The template it was started from, if any. ``ON DELETE SET NULL`` —
       deleting a template must never delete workout history.
   * - started_at
     - datetime
     -
   * - completed_at
     - datetime, nullable
     - Null = active/in-progress
   * - notes
     - text, nullable
     -
   * - body_weight
     - decimal, nullable
     - Optional snapshot of body weight for that session (convenience
       duplicate of a same-day ``BodyweightEntry``, not a foreign key,
       since the two are logged independently)

.. _model-workoutexercise:

``WorkoutExercise``
~~~~~~~~~~~~~~~~~~~~

One exercise block within a workout.

.. list-table::
   :widths: 22 22 56
   :header-rows: 1

   * - Column
     - Type
     - Notes
   * - id
     - PK
     -
   * - workout_id
     - FK -> Workout
     - Cascade delete with workout
   * - exercise_id
     - FK -> ExerciseTemplate
     -
   * - position
     - int
     - Order within the workout
   * - notes
     - text, nullable
     - e.g. ``felt heavy today`` — also used to carry a note when a
       historical entry recorded that the exercise was done but no set
       numbers were captured (see :doc:`data_migration`)

.. _model-workoutset:

``WorkoutSet``
~~~~~~~~~~~~~~~

.. list-table::
   :widths: 22 22 56
   :header-rows: 1

   * - Column
     - Type
     - Notes
   * - id
     - PK
     -
   * - workout_exercise_id
     - FK -> WorkoutExercise
     - Cascade delete with the exercise block
   * - position
     - int
     - Set number within the exercise block
   * - weight
     - decimal, nullable
     - Null for bodyweight/time/cardio-only entries
   * - weight_unit
     - enum(``lbs``/``kg``), nullable
     - Stored per-set as entered, so historical sets keep their original
       unit even if the user's display preference changes later
   * - reps
     - int, nullable
     -
   * - duration_seconds
     - int, nullable
     - Used by ``time`` and ``cardio`` tracking types
   * - distance_meters
     - decimal, nullable
     - Used by ``cardio`` tracking type; stored canonically in meters,
       displayed in mi/km per settings
   * - rest_seconds
     - int, nullable
     - How long to rest after this set, in seconds — logged data, not a
       config value (see :doc:`features/rest_timers`). Null until you type
       one or complete the set (which saves the value the timer used); a null
       field shows ghost text derived from the earlier sets in the block and
       from last time. Not copied to new sets by "+ Add set".
   * - is_warmup
     - bool, default false
     - Excluded from PR/1RM calculations
   * - is_dropset
     - bool, default false
     - A drop set performed immediately after the previous set at reduced
       weight, no rest between
   * - rpe
     - decimal, nullable
     - Optional rate-of-perceived-exertion, 1-10 in 0.5 increments
   * - completed
     - bool, default true
     - ``false`` for a set that was pre-filled (e.g., from a template's
       target) but not actually performed yet, while a workout is active

.. _model-bodyweightentry:

``BodyweightEntry``
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 22 22 56
   :header-rows: 1

   * - Column
     - Type
     - Notes
   * - id
     - PK
     -
   * - recorded_at
     - date
     - One entry per day (unique constraint)
   * - weight
     - decimal
     -
   * - unit
     - enum(``lbs``/``kg``)
     -

.. _model-usersettings:

``UserSettings``
~~~~~~~~~~~~~~~~~

Singleton row (``id = 1``), created on first app boot.

.. list-table::
   :widths: 22 22 56
   :header-rows: 1

   * - Column
     - Type
     - Notes
   * - weight_unit
     - enum(``lbs``/``kg``)
     - Default unit for *new* entries; does not retroactively convert
       stored sets
   * - distance_unit
     - enum(``mi``/``km``)
     -
   * - default_rest_seconds
     - int
     - App-wide rest timer default (seeded to 90s)
   * - theme
     - enum(``system``/``light``/``dark``)
     -

Set tracking types
-------------------

Rather than a separate table per exercise type, ``WorkoutSet`` has nullable
typed columns and ``ExerciseTemplate.tracking_type`` tells the frontend
which of them apply. This keeps "all logged weights for exercise X over time" a
single-table scan instead of a union across subtype tables:

.. list-table::
   :widths: 25 25 25 25
   :header-rows: 1

   * - tracking_type
     - fields used
     - example exercises
     - fields hidden in UI
   * - ``weight_reps``
     - weight, reps
     - Bench Press, Squat, Deadlift
     - duration, distance
   * - ``bodyweight_reps``
     - reps (weight optional, for e.g. a weighted vest)
     - Push Up, Pull Up, Sit Up
     - duration, distance
   * - ``time``
     - duration_seconds
     - Plank, Side Plank, Stretching
     - weight, reps, distance
   * - ``cardio``
     - duration_seconds, distance_meters (distance optional)
     - Treadmill Run, Rowing Machine, Stair Stepper
     - weight, reps

Business rules
---------------

- **Estimated 1RM** uses the Epley formula: ``weight * (1 + reps / 30.0)``,
  computed only from non-warmup ``weight_reps`` sets with ``reps >= 1``.
  Single-rep sets return the raw weight (no extrapolation needed).
- **Personal records** are computed on read (not stored) per exercise:
  heaviest weight ever, best estimated 1RM, best single-set volume
  (weight × reps), and — for ``cardio`` exercises — longest distance and
  fastest pace. See :doc:`api/stats`.
- **Only one active workout** at a time: starting a new workout while one
  is in progress is rejected by the API (409) — the client should prompt
  to finish or discard the in-progress one first.
- **Deleting a template never deletes workout history** (``template_id``
  is nullable + ``SET NULL`` on delete); deleting an exercise that has
  logged history is blocked by the API rather than cascading, to protect
  historical data — custom exercises with no history may be deleted
  freely.
- **Units are stored per-entry, not globally converted.** Changing the
  display unit in Settings only changes how existing values are
  *displayed* (a stored ``lbs`` set is converted for display, not
  rewritten); new sets are recorded in whatever unit was active when
  logged.
