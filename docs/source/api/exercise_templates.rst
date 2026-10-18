Exercises
=========

See :ref:`model-exercisetemplate`/:ref:`model-customexercisetemplate` and
:doc:`../features/exercise_library` for what an exercise is and how it's
used; this page is just the endpoint contract. There are two *tables*
behind "an exercise" now, in two separate databases
(:doc:`../data_model`'s "Database split") — a dataset-sourced
``ExerciseTemplate`` (the shared catalog) and a user-authored
``CustomExerciseTemplate`` — but one JSON shape: ``serialize_exercise_template``
produces the same fields either way (dataset-only fields read back
``null``/empty for a custom one), so a list mixing both kinds, or a
detail/stats/history/plan-preview response for either, all look the same
except for ``is_custom`` and which of ``id`` vs. nothing further
distinguishes them to a client that already knows which endpoint it called.

Since the two tables each have their own independent id sequence, **a
plain id is not by itself enough to say which exercise is meant** — a
catalog exercise and a custom one can share the same id. Anywhere a
request needs to name a *specific* exercise instead of just listing them,
the catalog and custom cases are two different endpoints (below), or (for
``exercise_id``/``custom_exercise_id`` in a workout/template exercise
body) two different fields, exactly one of which is given.

``GET /api/muscle-groups``
   List all muscle groups, ``[{id, name, display_order}]``.

``GET /api/muscle-groups/:id/muscles``
   The muscles that make up this group — e.g. Pectoralis Major under
   Chest — sorted by name, limited to muscles that group's exercises
   actually train as *primary*. Membership comes from the fixed
   ``GROUP_MUSCLES`` training-group mapping (see :doc:`../data_model`),
   not from scanning exercises alone, so a stray primary doesn't leak
   into the wrong group's chip.

``GET /api/muscles/recency``
   Days since each muscle was last trained (see :doc:`../data_flow`).
   ``{in_need_days: 8, muscles: {<slug>: {last_trained, days_since,
   regions}}}`` — a muscle never trained is left out entirely. Backs the
   home screen's recency map, the generate panel's group ranking, and the
   exercise library's muscle-filter ordering.

``GET /api/exercise-templates``
   List/search, merging the catalog and this user's own custom exercises
   into one result (two queries, one against each database, combined in
   Python — see ``routes/exercise_templates.py:list_exercise_templates``).
   Query params: ``q`` (name search — fuzzy: word order doesn't matter and
   a single typo is tolerated, ranked best match first; see
   ``services/search.py`` and :doc:`../features/exercise_library`),
   ``muscle_group_id`` (this app's own ``MuscleGroup``, filters the real
   column directly — ``404`` if unknown), ``muscle`` (a canonical slug —
   a catalog exercise matches via the ``ExerciseMuscle`` link table, a
   custom one by checking its own ``primary_muscles``/``secondary_muscles``
   JSON directly), ``equipment`` (this app's fixed vocabulary),
   ``tracking_type``, ``body_part`` (exact match against the dataset's own
   vocabulary — catalog exercises only; a custom exercise never has one,
   so this filter excludes all of them), ``is_custom``
   (``true``/``false``/omitted for both), ``limit`` (default 40, capped at
   100), ``offset``. Each item includes ``last_performed`` (date + a short
   summary of the last logged set, or omitted if never logged) for
   list-view display, plus the dataset-sourced content on a catalog item
   (``null``/empty on a custom one): ``image_url`` / ``image_urls``,
   ``instruction_steps``, ``tips``, ``difficulty``, ``mechanic``, ``attribution``,
   and ``primary_muscles`` / ``secondary_muscles`` as
   ``[{slug, name, image_url, regions}]`` — canonical muscle slugs (see
   :ref:`model-muscle`), not the source dataset's own wording; ``image_url``
   is ``null`` unless RepDB has a diagram for that muscle, and ``regions``
   are the body-map SVG region(s) it lights up (:doc:`../data_flow`).

``GET /api/exercise-templates/facets``
   ``{body_parts: [...], equipment: [...]}`` — every distinct dataset
   ``body_part``/``equipment_raw`` value currently present, for building
   filter UIs against the dataset's own vocabulary (as opposed to
   ``muscle_group_id``/``equipment`` above, which filter by this app's own
   vocabulary instead). Catalog-only, naturally, since those are dataset
   fields.

``GET /api/exercise-templates/:id``
   Full detail of a **catalog** exercise, same shape as a list item, plus
   ``last_performed``. ``404`` for a custom exercise's id (even if it
   happens to also be a valid catalog id for a *different* exercise — see
   above) — use the ``/custom-exercise-templates/:id`` sibling below for
   those.

``PATCH /api/exercise-templates/:id``
   The *only* editable thing on a catalog exercise: this user's own
   ``notes`` (see :ref:`model-catalogexercisenote`) — name, equipment,
   muscle group etc. are shared, common data this user-facing endpoint
   never changes (only the seed script does, and only when first creating
   a row). Body: ``{notes}`` (``null``/blank deletes the note).

``DELETE /api/exercise-templates/:id``
   Always refused with ``409`` — a catalog exercise is shared data, common
   to every user, not this user's to delete (``404`` if the id doesn't
   exist at all). Deleting one from the catalog itself means removing it
   from the dataset and re-seeding.

``POST /api/custom-exercise-templates``
   Create a custom exercise. Body: ``name`` (required),
   ``muscle_group_id`` (required — the catalog's, see
   :ref:`model-musclegroup`), ``equipment``, ``tracking_type``, ``notes``.

``GET /api/custom-exercise-templates/:id``
   Full detail of a **custom** exercise, same shape and caveats as the
   catalog ``GET`` above, reversed.

``PATCH /api/custom-exercise-templates/:id``
   Partial update of any of ``name``, ``muscle_group_id``, ``equipment``,
   ``tracking_type``, ``notes`` — a custom exercise is this user's own
   row, so (unlike the catalog) all of it is editable.

``DELETE /api/custom-exercise-templates/:id``
   Returns ``409`` if any ``WorkoutSet`` references it (directly via its
   ``WorkoutExercise``/``TemplateExercise`` blocks' ``custom_exercise_id``)
   — see :ref:`data_model:Business rules`.

``GET /api/exercise-templates/:id/image``, ``GET /api/exercise-templates/:id/image/:n``
   Streams one of the template's images straight out of the dataset
   submodules: image ``n`` (default ``0``) of its RepDB poses
   (``0`` = start, ``1`` = peak; single-pose exercises have only ``0``), falling
   back to the original dataset's single image for ``n = 0`` when RepDB has
   none (or its file is missing). ``404`` for a template with no image
   (a custom exercise never has one — there's no sibling route for this,
   since nothing ever gives it an image to serve), an out-of-range ``n``,
   or a missing file. Served with a one-day ``Cache-Control``. The
   list/detail responses give the URLs directly as ``image_url`` (the
   first) and ``image_urls`` (all).

``GET /api/muscles/:slug/image``
   RepDB's highlighted-body diagram for a muscle (``slug`` is the underscore
   form, e.g. ``pectoralis_major``). ``404`` if RepDB has no diagram under that
   name (27 do) or the slug isn't ``[a-z0-9_]+``. List/detail responses only
   include an ``image_url`` on a muscle when its diagram exists.

``GET /api/exercise-templates/:id/history``, ``GET /api/custom-exercise-templates/:id/history``
   Every ``WorkoutExercise`` block for this (catalog or custom,
   respectively) exercise, most recent first, with its sets nested.
   Paginated (``limit``/``offset``).

``GET /api/exercise-templates/:id/plan-preview``, ``GET /api/custom-exercise-templates/:id/plan-preview``
   What starting a workout with this (catalog or custom, respectively)
   exercise would plan right now — runs the exact same
   :doc:`progressive overload <../features/progressive_overload>`
   calculation a real workout start uses (``sets_plan.py:plan_sets``),
   without creating anything. Query params mirror a ``TemplateExercise``:
   ``warmup_sets``, ``target_sets``, ``drop_sets`` (each an int, default
   ``0``/``1``/``0``), ``target_reps`` (optional). Returns a bare list of
   planned sets — the same shape as a ``WorkoutSet``'s ``planned_*``
   fields, minus the id/position wrapper since nothing is actually
   created: ``is_warmup``, ``is_dropset``, ``weight``, ``weight_unit``,
   ``reps``, ``duration_seconds``, ``is_progressed``,
   ``is_progression_active`` (see :ref:`model-workoutset`'s
   ``planned_progression_active``). ``404`` if the exercise doesn't exist.
   Powers the template editor's live preview
   (:doc:`../features/templates`).

``GET /api/exercises/:id/stats``, ``GET /api/custom-exercises/:id/stats``
   See :doc:`stats`. The catalog one is kept at the old ``/api/exercises``
   path rather than moved, for history's sake; the custom one is a
   sibling at the analogous ``/api/custom-exercises`` path rather than
   ``/api/custom-exercise-templates`` for symmetry with it.
