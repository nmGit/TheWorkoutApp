Data model
==========

The schema is relational (SQLAlchemy models, Alembic-versioned) so that
cross-exercise analytical queries — "every logged weight for Bench Press,
in order" — are plain joins, not application-level scans of nested
documents.

Database split
----------------

There are **two** SQLite databases, not one, each with its own
``SQLALCHEMY_BINDS`` entry (``"catalog"``) and its own connection string
(``DATABASE_URL`` for the user one — the default bind — and
``CATALOG_DATABASE_URL`` for the catalog):

- **The catalog** (``ExerciseTemplate``, ``Muscle``, ``ExerciseMuscle``,
  ``MuscleGroup``): the shared, vendored exercise reference data — common
  to every user, never written to by a user action. Rebuilt from the
  bundled dataset submodules by ``scripts/seed_exercise_templates.py``
  rather than hand-migrated with Alembic (that script, not a migration,
  is this database's schema/data source of truth).
- **The user database** (everything else — ``Workout``,
  ``WorkoutExercise``, ``WorkoutSet``, ``WorkoutTemplate``,
  ``TemplateExercise``, ``CustomExerciseTemplate``,
  ``CatalogExerciseNote``, ``UserSettings``, ``BodyweightEntry``): this
  user's own data. This is the database a future multi-user deployment
  multiplies — each user gets their own copy of it, all reading the one
  shared catalog — this split is the first step toward that, not the
  whole of it (there's still only ever one user database and no login/
  account system yet).

This matters for how exercises are referenced. A workout/template
exercise "slot" (``WorkoutExercise``, ``TemplateExercise``) can point at
either a catalog exercise or this user's own custom one, and the two live
in different database *files* — SQLite can't enforce a foreign key across
them, and each table has its own independent id sequence, so a catalog
exercise and a custom one can share the same id. Both tables therefore
carry **two** nullable columns, ``exercise_id`` (catalog, unenforced) and
``custom_exercise_id`` (same database, a real enforced foreign key), with
a ``CHECK`` constraint that exactly one is ever set
(``ExerciseReferenceMixin``, ``models/exercise_reference.py``). Application
code reads whichever is set through a single ``.exercise`` property
(resolves to an ``ExerciseTemplate`` or a ``CustomExerciseTemplate``,
whichever one `is None` — see the model for how) rather than branching on
the two columns everywhere, and anything that needs to group/compare "the
same exercise" across rows (progression history, strength-score
baselines, ...) uses ``.exercise_ref`` — an ``(exercise | custom, id)``
pair — as its key instead of a bare id, since a bare id is exactly the
thing that can collide.

A **note** on a catalog exercise (the free-text "stay at 60 until my form
is good" kind) can't be a column on the catalog row either, once that row
is common to every user — it's personal commentary, not a correction to
the shared exercise, so it lives in this user's own database instead
(``CatalogExerciseNote``, a one-row-per-noted-exercise table keyed by the
catalog exercise's id, also unenforced for the same cross-file reason).
``ExerciseTemplate.notes`` is a Python property backed by that table, not
a real column, so code that reads ``exercise.notes`` doesn't need to know
the difference.

A ``CustomExerciseTemplate`` doesn't use the ``Muscle``/``ExerciseMuscle``
link tables at all (those are catalog-only) — its muscles are plain
canonical-slug strings in two JSON columns, since a slug is already a
stable, self-describing identifier that doesn't need a row of its own
the way the catalog's muscle-name reconciliation
(``services/muscle_catalog.py``) does.

See ``scripts/split_catalog_database.py`` for the one-time script that
performed this split on an existing combined database (and the
``l0d3a8f5c2e9``/``m1e4b9a6d3f0`` migrations either side of it), and
:doc:`review` for the change itself.

Entity-relationship overview
-----------------------------

The catalog and user databases are drawn together here for readability,
but — per the above — they're two separate files; nothing below crosses
them with an actual foreign key.

.. mermaid::

   erDiagram
       MuscleGroup ||--o{ ExerciseTemplate : has
       ExerciseTemplate ||--o{ ExerciseMuscle : has
       Muscle ||--o{ ExerciseMuscle : "worked by"
       ExerciseTemplate ||--o{ TemplateExercise : "used by (catalog)"
       CustomExerciseTemplate ||--o{ TemplateExercise : "used by (custom)"
       ExerciseTemplate ||--o{ CatalogExerciseNote : "noted by"
       WorkoutTemplate ||--o{ TemplateExercise : has
       WorkoutTemplate ||--o{ Workout : "started from (optional)"
       ExerciseTemplate ||--o{ WorkoutExercise : "used by (catalog)"
       CustomExerciseTemplate ||--o{ WorkoutExercise : "used by (custom)"
       Workout ||--o{ WorkoutExercise : has
       WorkoutExercise ||--o{ WorkoutSet : has

       BodyweightEntry {
           date recorded_at
           decimal weight
       }
       UserSettings {
           int id "singleton, always 1"
       }

Two different things are both informally called a "muscle group" in this
codebase, and they don't share rows:

- ``MuscleGroup`` (above) is the exercise **catalog's** fixed list —
  Chest, Back, Shoulders, Arms, Core, Legs, Cardio, Full Body, Mobility —
  used for browsing/filtering the exercise library.
- The **training groups** used to rank what's due for generated workouts
  (:doc:`features/generated_workouts`) are a separate, hard-coded mapping,
  ``GROUP_MUSCLES`` in ``services/exercise_templates.py``: Chest, Back,
  Shoulders, Arms, Core, Legs, each a fixed set of canonical muscle slugs.
  There's no database table for these — they only exist in that one
  module constant, consulted by ``services/generate.py``. Cardio,
  Mobility and Full Body intentionally have no training group, since
  generated workouts don't rank them.

``ExerciseTemplate`` (catalog, dataset-sourced only now) and
``CustomExerciseTemplate`` (user data, this user's own) are "what is this
exercise", between them: name, muscle group, equipment, tracking type,
description. A saved routine's slot (``TemplateExercise``) and a
workout's logged block (``WorkoutExercise``) link to whichever one an
exercise actually is (see "Database split" above). There is no separate
per-user "Exercise" entity beyond that: this used to be two tables (a
personal ``Exercise`` linked via a nullable ``template_id`` to a dataset/
custom ``ExerciseTemplate``); they were merged into one ``ExerciseTemplate``
(custom and dataset rows together, distinguished by an ``is_custom``
column) after that nullable link let two different exercises collide onto
one template (see :doc:`review` for the incident and
:doc:`data_migration` for the merge itself) — and later split back into
two tables, this time along the catalog/user-data line rather than the
original per-user-row line, once a shared catalog across future users
needed its own database (see "Database split" above; also :doc:`review`).
``ExerciseTemplate`` additionally carries image/instructions metadata from
the bundled dataset submodules (RepDB and/or the original
exercises-dataset) that ``CustomExerciseTemplate`` has no use for — that
and where they live are the only real differences between the two;
filtering, editing, logging and stats are otherwise symmetric.

Core tables
-----------

.. _model-musclegroup:

``MuscleGroup``
~~~~~~~~~~~~~~~~

**Catalog** (shared) data — the app's one fixed list, used by dataset and
custom exercises alike (a ``CustomExerciseTemplate.muscle_group_id``
references this table too, just not as an enforced ``db.ForeignKey`` —
see "Database split" above).

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

**Catalog** (shared) data — lives in the ``"catalog"`` bind, a separate
database file; see "Database split" above. A dataset-sourced exercise,
the abstract idea of it — sourced from the bundled dataset submodules
(RepDB at ``external/repdb-exercise-dataset`` and the original
``external/exercises-dataset``, both imported by
``scripts/seed_exercise_templates.py``). A user-authored exercise is a
``CustomExerciseTemplate`` instead (below), a different table in the
other database, never a row here. A template can carry both dataset
sources' data: each source's own fields are stored exactly as that source
provides them, RepDB's images/text/muscles are preferred wherever
present, and the original's are the fallback. The app-owned fields
(``name``, ``equipment``, ``tracking_type``, ``muscle_group_id``) are set
by seeding only when it creates the row, never refreshed on a re-run, so
edits made in the app survive. See :doc:`features/exercise_library` for
how these surface in the UI.

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
   * - (``notes`` property)
     - computed, not a column
     - This user's own note about this exercise (e.g. form cues), read from
       ``CatalogExerciseNote`` (user data, the other database) and written
       through a property setter that creates/updates/deletes that row --
       see :ref:`model-catalogexercisenote`. Not a real column here, since
       a note is personal commentary, not catalog data.
   * - category / body_part / target_muscle / muscle_group
     - string, nullable
     - The dataset's own vocabulary/classification (e.g. ``body_part:
       upper legs``) — display/reference only, never used for filtering.
       Null for custom templates. ``target_muscle``/``muscle_group`` here
       are leftover plain-text dataset fields, superseded by the
       ``muscle_links`` relationship below; nothing reads them anymore.
   * - (muscles worked)
     - via ``muscle_links`` → ``ExerciseMuscle`` → ``Muscle``
     - Not a column on this table. ``primary_muscles``/``secondary_muscles``
       are Python properties that read ``muscle_links`` (filtering by
       ``role``) — see :ref:`model-muscle` below. This replaced an earlier
       pair of JSON list-of-strings columns holding each dataset's raw,
       uncanonicalised muscle names (``pectorals`` vs. ``pectoralis_major``
       for the same muscle); seeding now resolves every raw name to one
       canonical ``Muscle`` row via ``services/muscle_catalog.py``.
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
   * - created_at
     - datetime
     -
   * - (``is_custom`` property)
     - computed, not a column
     - Always ``False`` here (a custom exercise is never a row in this
       table) — kept as a property so code checking ``exercise.is_custom``
       works the same on either this or a ``CustomExerciseTemplate``,
       without an ``isinstance`` check at every call site.
   * - (``ref`` property)
     - computed, not a column
     - ``("catalog", self.id)`` — a collision-free identity for this
       exercise (plain ``id`` isn't unique across the catalog/custom
       split — see "Database split" above). Compare against
       ``CustomExerciseTemplate.ref``'s ``("custom", id)``, and
       ``WorkoutExercise``/``TemplateExercise``'s own ``.exercise_ref``.
   * - (``is_stretch`` property)
     - computed, not a column
     - ``True`` when ``category == "stretching"`` or the exercise's
       ``MuscleGroup`` is ``Mobility``. Excludes the exercise from
       strength scoring, muscle recency, and generated-workout picks —
       stretching a muscle isn't training its strength. A handful of
       dataset entries that are really stretches (an adductor stretch, a
       yoga pose) are mis-classified as ``weight_reps`` under a strength
       muscle group upstream and so are *not* caught by this — known,
       not yet corrected.

.. _model-customexercisetemplate:

``CustomExerciseTemplate``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**User data** — lives in the default bind, this user's own database. An
exercise authored from scratch rather than sourced from a dataset. Exposes
the same read interface as ``ExerciseTemplate`` wherever the two are used
interchangeably (``is_custom``, ``is_stretch``, ``ref``,
``primary_muscles``/``secondary_muscles``, and every field
``serialize_exercise_template`` reads) so calling code doesn't need to
know or care which one it got; dataset-only fields it has no use for
(``external_id``, ``instructions``, image paths, ...) are plain class
attributes returning ``None``/empty rather than real columns, since
nothing ever sets them for a custom exercise.

.. list-table::
   :widths: 22 22 56
   :header-rows: 1

   * - Column
     - Type
     - Notes
   * - id
     - PK
     - Its own sequence, independent of ``ExerciseTemplate.id`` — the two
       can and do collide (see "Database split" above); never compared
       against an ``ExerciseTemplate`` id without also checking which
       table it came from.
   * - name
     - string
     -
   * - equipment
     - string, nullable
     - This app's fixed vocabulary, same as ``ExerciseTemplate.equipment``.
   * - tracking_type
     - enum, nullable
     - Same ``TRACKING_TYPES`` as ``ExerciseTemplate``.
   * - muscle_group_id
     - int, nullable
     - References the catalog's ``MuscleGroup.id`` — not a ``db.ForeignKey``
       (that table is in the other database file, which SQLite can't
       enforce a constraint across), resolved at the app layer instead.
   * - notes
     - text, nullable
     - A real column here (unlike ``ExerciseTemplate.notes``) — this whole
       row already belongs to one user, so there's no shared-row problem
       to route around with an overlay table.
   * - primary_muscles / secondary_muscles
     - JSON list of strings, nullable
     - Canonical muscle slugs directly (e.g. ``["pectoralis_major"]``), not
       via a link table — a slug is already a stable, self-describing
       identifier that doesn't need a row of its own the way the
       catalog's muscle-name reconciliation does. Exposed as Python
       properties of the same name, so reading/writing them looks
       identical to ``ExerciseTemplate``'s ``ExerciseMuscle``-backed ones.
   * - created_at
     - datetime
     -

.. _model-catalogexercisenote:

``CatalogExerciseNote``
~~~~~~~~~~~~~~~~~~~~~~~~~

**User data** — lives in the default bind. This user's own note about a
*catalog* exercise (see ``ExerciseTemplate.notes`` above). One row per
noted exercise; a blank note deletes the row rather than storing an empty
string.

.. list-table::
   :widths: 22 22 56
   :header-rows: 1

   * - Column
     - Type
     - Notes
   * - exercise_id
     - PK, int
     - References the catalog's ``ExerciseTemplate.id`` — not a
       ``db.ForeignKey``, same reason as ``CustomExerciseTemplate.muscle_group_id``.
   * - notes
     - text
     -

.. _model-muscle:

``Muscle``
~~~~~~~~~~~

**Catalog** (shared) data. One row per canonical muscle (35 of them) — the
vocabulary every catalog exercise's worked muscles key off of.
``services/muscle_catalog.py`` is the only place that resolves a
dataset's raw muscle wording (``pectorals``, ``chest``, ...) to one of
these; everywhere else in the app, a muscle is just its ``slug`` — which
is also why a ``CustomExerciseTemplate`` doesn't link here at all, just
stores slug strings directly (see above).

.. list-table::
   :widths: 22 22 56
   :header-rows: 1

   * - Column
     - Type
     - Notes
   * - id
     - PK
     -
   * - slug
     - string, unique
     - e.g. ``pectoralis_major``, ``biceps_brachii``
   * - name
     - string
     - Display name, e.g. ``Pectoralis Major``

Body regions (what's actually drawn on the body-map SVG) are a further,
many-to-many mapping on top of this — ``services/muscle_regions.py`` — not
stored in the database at all; see :doc:`features/strength_score` and
:doc:`architecture`.

.. _model-exercisemuscle:

``ExerciseMuscle``
~~~~~~~~~~~~~~~~~~~~

**Catalog** (shared) data. The link table behind
``ExerciseTemplate.primary_muscles`` / ``secondary_muscles`` (properties,
not real columns — see above); only ever links a *catalog* exercise — a
``CustomExerciseTemplate`` never has rows here (see above).

.. list-table::
   :widths: 22 22 56
   :header-rows: 1

   * - Column
     - Type
     - Notes
   * - exercise_id
     - FK -> ExerciseTemplate, PK (composite)
     - Cascade delete with the exercise
   * - muscle_id
     - FK -> Muscle, PK (composite)
     -
   * - role
     - string (``primary``/``secondary``)
     - A muscle is never linked as both for the same exercise — setting
       one role for a muscle already linked under the other replaces it.

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
     - int, nullable
     - References the catalog's ``ExerciseTemplate.id`` — not a
       ``db.ForeignKey`` (different database file; see "Database split"
       above). Exactly one of this and ``custom_exercise_id`` is set,
       enforced by a ``CHECK`` constraint
       (``ExerciseReferenceMixin``, ``models/exercise_reference.py``).
   * - custom_exercise_id
     - FK -> CustomExerciseTemplate, nullable
     - Same database as this table, so a real enforced foreign key. See
       ``exercise_id`` above.
   * - (``exercise`` property)
     - computed, not a column
     - Whichever of the two is actually set, resolved from whichever
       database it lives in — code reads ``te.exercise`` rather than
       branching on the two columns itself.
   * - position
     - int
     - Order within the template
   * - target_sets
     - int, nullable
     - How many **working** sets (see :doc:`features/progressive_overload`)
   * - warmup_sets / drop_sets
     - int, default 0
     - How many warm-up/drop sets come before/after the working sets.
       Always copy that same kind of set from last session, unchanged —
       never progressed.
   * - target_reps
     - string, nullable
     - Free-form, e.g. ``8-12`` or a single number. Despite the name,
       this is this exercise's **rep-range override** for progressive
       overload (:doc:`features/progressive_overload`), not a literal
       target repeated every set — left null, the exercise uses the
       global default rep range from Settings.
   * - target_weight
     - decimal, nullable
     - Set by "Save as template from a workout" (the last logged weight)
       and accepted on write, but not read by anything at runtime —
       progression computes the next weight from history instead. A
       candidate for removal.
   * - superset_group
     - int, nullable
     - Set, with an identical value, on exactly one other **adjacent**
       (by ``position``) exercise to pair the two into a
       :doc:`superset <features/supersets>`. Not a globally unique id —
       only scoped to this template's own exercises. See
       ``services/supersets.py``.

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
     - int, nullable
     - References the catalog's ``ExerciseTemplate.id`` — see
       ``TemplateExercise.exercise_id`` above; same two-column,
       exactly-one-set design (``ExerciseReferenceMixin``).
   * - custom_exercise_id
     - FK -> CustomExerciseTemplate, nullable
     - See ``TemplateExercise.custom_exercise_id`` above.
   * - (``exercise`` property)
     - computed, not a column
     - See ``TemplateExercise.exercise`` above.
   * - position
     - int
     - Order within the workout
   * - notes
     - text, nullable
     - e.g. ``felt heavy today`` — also used to carry a note when a
       historical entry recorded that the exercise was done but no set
       numbers were captured (see :doc:`data_migration`)
   * - superset_group
     - int, nullable
     - Same meaning as ``TemplateExercise.superset_group`` above, scoped
       to this workout instead: set identically on exactly one other
       adjacent exercise to pair the two into a
       :doc:`superset <features/supersets>`, forcing equal set counts
       between them. See ``services/supersets.py``.

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
     - Excluded from PR/1RM calculations, strength scoring
       (:doc:`features/strength_score`), muscle recency
       (:doc:`features/generated_workouts`), and progressive overload
       (:doc:`features/progressive_overload`) — a warm-up is never
       counted as evidence of what you can actually lift.
   * - is_dropset
     - bool, default false
     - A drop set performed immediately after the previous set at reduced
       weight, no rest between. Excluded from the same things
       ``is_warmup`` is, for the same reason.
   * - planned_weight / planned_weight_unit / planned_reps /
       planned_duration_seconds
     - decimal / enum / int / int, all nullable
     - What a set started from a template or a generated workout is
       expected to be — filled in by :doc:`features/progressive_overload`
       (working sets) or copied from last session (warm-ups/drops), *not*
       written into the real entered columns above. The set row shows
       these as ghost (placeholder) text. Completing the set
       (``PATCH /api/sets/:id {completed: true}``) copies whichever of
       ``weight``/``reps``/``duration_seconds`` are still null from these,
       then clears all four — so a completed set never has both a real
       and a planned value at once. A **blank** workout's sets are the
       one case that never gets planned values (nothing populates them),
       so they fall back to plain "last time" ghost text computed
       client-side instead.
   * - planned_is_progressed
     - bool, default false
     - ``True`` only when the ``planned_*`` values above are actually
       different from what progressive overload compared them against —
       a real increase, not just progression having run (double
       progression in particular can compute a target that matches what
       was already demonstrated, e.g. catching a weaker set up to the
       session's best one). Cleared alongside the ``planned_*`` fields
       when the set is completed. Drives the ghost text's color and the
       green "P" badge — see :doc:`features/progressive_overload`.
   * - planned_progression_active
     - bool, default false
     - ``True`` whenever progressive overload actually ran for this set
       (there's an earlier session to progress from, and it isn't off in
       Settings), whether or not it changed anything —
       ``planned_is_progressed`` implies this, but not the reverse.
       Always ``False`` for a plain copy (warm-ups, drops, progression
       off, or no earlier session). Cleared alongside the ``planned_*``
       fields when the set is completed. Drives the grey "P" badge when
       ``planned_is_progressed`` is ``False`` but this is ``True``.
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
     - enum(``system``/``light``/``dark``/``green``/``pink``)
     -
   * - progression_method
     - enum(``double``/``linear``/``off``), default ``double``
     - See :doc:`features/progressive_overload`
   * - experience
     - enum(``novice``/``intermediate``), default ``intermediate``
     - Stored, not yet read by the progression calculation
   * - load_step_lb / load_step_kg
     - float, default 5.0 / 2.5
     - How much weight progression adds at a time, per unit
   * - default_rep_range
     - string(12), default ``"8-12"``
     - Used by progression for any ``TemplateExercise`` whose own
       ``target_reps`` is null

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
  computed only from non-warmup sets with ``reps >= 1``. Single-rep sets
  return the raw weight (no extrapolation needed). For a
  ``bodyweight_reps`` set, ``weight`` here means body weight (the nearest
  logged ``BodyweightEntry`` on or before the set's workout) plus the
  set's own ``weight`` field (any added load, normally 0) — not the added
  load alone, since that's not the exercise's real load. ``None`` if body
  weight has never been logged at all (``WorkoutSet.estimated_one_rm``).
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
- **Per-exercise PRs and the per-muscle strength score are two separate
  pipelines that both use the Epley formula, computed differently.** PRs
  (above, :doc:`api/stats`) are the best-ever raw value for one exercise,
  forever. The strength score (:doc:`features/strength_score`) is a
  per-muscle, per-session ratio against a recent rolling baseline, pooled
  across every exercise that works that muscle. A new PR and a below-1.0
  strength score can happen in the same workout, and both are correct.
