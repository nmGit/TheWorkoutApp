Exercises
=========

See the :ref:`model-exercisetemplate` table and
:doc:`../features/exercise_library` for what a template is and how it's
used; this page is just the endpoint contract. There is no separate
"exercise" resource — an ``ExerciseTemplate`` *is* the exercise, whether
dataset-sourced or custom (see :doc:`../review` for why the two used to be
separate rows, and why that was a bug).

``GET /api/muscle-groups``
   List all muscle groups, ``[{id, name, display_order}]``.

``GET /api/exercise-templates``
   List/search. Query params: ``q`` (name search), ``muscle_group_id``
   (this app's own ``MuscleGroup``, filters the real column directly —
   ``404`` if unknown), ``equipment`` (this app's fixed vocabulary),
   ``tracking_type``, ``body_part`` (exact match against the dataset's own
   vocabulary, dataset-sourced templates only), ``is_custom``
   (``true``/``false``), ``limit`` (default 40, capped at 100), ``offset``.
   Each item includes ``last_performed`` (date + a short summary of the
   last logged set, or omitted if never logged) for list-view display, plus
   the dataset-sourced content: ``image_url`` / ``image_urls``,
   ``instruction_steps``, ``tips``, ``difficulty``, ``mechanic``, ``attribution``,
   and ``primary_muscles`` / ``secondary_muscles`` as ``[{name, image_url}]``
   — the names are the source dataset's own, and ``image_url`` is ``null``
   unless RepDB has a diagram for that muscle.

``GET /api/exercise-templates/facets``
   ``{body_parts: [...], equipment: [...]}`` — every distinct dataset
   ``body_part``/``equipment_raw`` value currently present, for building
   filter UIs against the dataset's own vocabulary (as opposed to
   ``muscle_group_id``/``equipment`` above, which filter by this app's own
   vocabulary instead).

``POST /api/exercise-templates``
   Create a custom exercise (always ``is_custom: true`` — dataset-sourced
   templates are created only by the seed script). Body: ``name``
   (required), ``muscle_group_id`` (required), ``equipment``,
   ``tracking_type``, ``notes``.

``GET /api/exercise-templates/:id``
   Full detail, same shape as a list item, plus ``last_performed``.

``PATCH /api/exercise-templates/:id``
   Partial update of ``name``, ``muscle_group_id``, ``equipment``,
   ``tracking_type``, ``notes`` — never the dataset-sourced fields
   (``instructions``, ``image_path``, ``body_part``, etc.), which aren't
   user-editable for either kind of template.

``DELETE /api/exercise-templates/:id``
   Returns ``409`` if the template is dataset-sourced (``is_custom:
   false`` — deleting one would remove it from the catalog entirely; use
   ``git submodule update`` + re-seed if the dataset itself changes) or if
   any ``WorkoutSet`` references it (directly via its ``WorkoutExercise``
   blocks) — see :ref:`data_model:Business rules`.

``GET /api/exercise-templates/:id/image``, ``GET /api/exercise-templates/:id/image/:n``
   Streams one of the template's images straight out of the dataset
   submodules: image ``n`` (default ``0``) of its RepDB poses
   (``0`` = start, ``1`` = peak; single-pose exercises have only ``0``), falling
   back to the original dataset's single image for ``n = 0`` when RepDB has
   none (or its file is missing). ``404`` for a template with no image
   (e.g. a custom one), an out-of-range ``n``, or a missing file. Served with
   a one-day ``Cache-Control``. The list/detail responses give the URLs
   directly as ``image_url`` (the first) and ``image_urls`` (all).

``GET /api/muscles/:slug/image``
   RepDB's highlighted-body diagram for a muscle (``slug`` is the underscore
   form, e.g. ``pectoralis_major``). ``404`` if RepDB has no diagram under that
   name (27 do) or the slug isn't ``[a-z0-9_]+``. List/detail responses only
   include an ``image_url`` on a muscle when its diagram exists.

``GET /api/exercise-templates/:id/history``
   Every ``WorkoutExercise`` block for this exercise, most recent first,
   with its sets nested. Paginated (``limit``/``offset``).

``GET /api/exercises/:id/stats``
   See :doc:`stats`. Kept at the old ``/api/exercises`` path rather than
   moved, since it's the one endpoint with no real "exercise vs. template"
   ambiguity to resolve either way.
