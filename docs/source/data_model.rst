Data model
==========

The schema is relational (SQLAlchemy models, Alembic-versioned) so that
cross-exercise analytical queries — "every logged weight for Bench Press,
in order" — are plain joins, not application-level scans of nested
documents.

Entity-relationship overview
-----------------------------

.. code-block:: text

   MuscleGroup 1───* Exercise 1───* TemplateExercise *───1 WorkoutTemplate
                         │                                      │
                         │                                      │ 1
                         │ 1                                    │
                         │                                      * (optional, workout.template_id)
                         *                                       │
                   WorkoutExercise *───────────────────────────1 Workout
                         │ 1
                         │
                         *
                     WorkoutSet

   BodyweightEntry            (standalone, date + weight)
   UserSettings                (singleton row)

Core tables
-----------

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

``Exercise``
~~~~~~~~~~~~

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
     - e.g. ``Bench Press``, ``Incline Bench (Dumbbell)``
   * - muscle_group_id
     - FK -> MuscleGroup
     -
   * - equipment
     - enum
     - ``barbell`` / ``dumbbell`` / ``machine`` / ``cable`` / ``bodyweight``
       / ``kettlebell`` / ``other``. Parsed from the trailing ``(...)`` in
       legacy names where present, defaults to ``other``.
   * - tracking_type
     - enum
     - ``weight_reps`` / ``bodyweight_reps`` / ``time`` / ``cardio``. Drives
       which input fields the logging UI shows (see
       :ref:`data_model:Set tracking types`).
   * - is_custom
     - bool
     - ``false`` for the seeded library, ``true`` for user-created exercises
   * - default_rest_seconds
     - int, nullable
     - Falls back to the global default in ``UserSettings`` when null
   * - notes
     - text, nullable
     - Free-text (form cues, etc.)

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
     - FK -> Exercise
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
     - FK -> Exercise
     -
   * - position
     - int
     - Order within the workout
   * - notes
     - text, nullable
     - e.g. ``felt heavy today`` — also used to carry a note when a
       historical entry recorded that the exercise was done but no set
       numbers were captured (see :doc:`data_migration`)

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
typed columns and ``Exercise.tracking_type`` tells the frontend which of
them apply. This keeps "all logged weights for exercise X over time" a
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
