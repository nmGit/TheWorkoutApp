Exercises
=========

``GET /api/muscle-groups``
   List all muscle groups, ``[{id, name, display_order}]``.

``GET /api/exercises``
   List exercises. Query params: ``q`` (name search), ``muscle_group_id``,
   ``equipment``. Each item includes ``last_performed`` (date + a short
   summary of the last logged set, or null) for list-view display.

``POST /api/exercises``
   Create an exercise (always ``is_custom: true`` — seeded exercises are
   created only by the migration/seed script). Body: ``name`` (required),
   ``muscle_group_id`` (required), ``equipment``, ``tracking_type``
   (required), ``default_rest_seconds``, ``notes``.

``GET /api/exercises/:id``
   Full exercise detail.

``PATCH /api/exercises/:id``
   Partial update of any editable field.

``DELETE /api/exercises/:id``
   Deletes the exercise. Returns ``409`` if any ``WorkoutSet`` references
   it (directly via its ``WorkoutExercise`` blocks) — see
   :ref:`data_model:Business rules`.

``GET /api/exercises/:id/history``
   Every ``WorkoutExercise`` block for this exercise, most recent first,
   with its sets nested. Paginated (``limit``/``offset``).

``GET /api/exercises/:id/stats``
   See :doc:`stats`.
