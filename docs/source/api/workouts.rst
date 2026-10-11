Workouts
========

``GET /api/workouts``
   List workouts, most recent first. Query params: ``status``
   (``active``/``completed``), ``template_id``, date range, pagination.
   List items are summaries (no nested sets — use the detail endpoint for
   those) but include ``exercise_count`` for the history row.

``GET /api/workouts/active``
   Returns the current in-progress workout (``completed_at IS NULL``) with
   exercises and sets fully nested, or ``204 No Content`` if none. The
   active-workout screen polls/refetches this on focus via TanStack Query.

``POST /api/workouts``
   Start a workout. Body: ``{template_id}`` (omit for blank). Returns
   ``409`` if a workout is already active. When started from a template,
   pre-creates ``WorkoutExercise``/``WorkoutSet`` rows from the template's
   warm-up/working/drop set counts, with ``completed: false`` and the
   working sets' next weight/reps computed by progressive overload (see
   :doc:`../features/progressive_overload` and :doc:`../data_flow`) —
   written to each set's ``planned_*`` fields, not its real ones.

``GET /api/workouts/generate/groups``
   The training groups (Chest/Back/Shoulders/Arms/Core/Legs) ranked by
   need, for the generate panel. Each entry: ``{name, in_need, trained}``
   (muscles in need, out of the group's currently-trained muscles). See
   :doc:`../features/generated_workouts`.

``POST /api/workouts/generated``
   Build and start a generated workout. Body: ``{count, stretching,
   cardio, familiar_first, groups}`` — ``count`` (1–10, required),
   ``groups`` (list of training-group names; omit to let the ranking
   above choose the top two). Returns ``409`` if a workout is already
   active, ``400`` if ``count`` is out of range or ``groups`` isn't a
   list of strings. See :doc:`../data_flow` for the selection algorithm.
   Each exercise's sets get the same progressive-overload treatment a
   template start's do (:doc:`../features/progressive_overload`), as
   plain working sets with no warm-ups/drops and no per-exercise
   rep-range override.

``GET /api/workouts/:id``
   Full detail: exercises and sets nested, in position order.

``PATCH /api/workouts/:id``
   Update ``name``/``notes``/``body_weight``, or set ``completed_at`` to
   finish it (dropping any sets left ``completed: false``, per
   :ref:`features/workout_logging:Finishing a workout`).

``DELETE /api/workouts/:id``
   Discards a workout (active or completed) entirely.

``POST /api/workouts/:id/exercises``
   Add an exercise block. Body: ``{exercise_id}``. Appended at the next
   ``position``.

``DELETE /api/workouts/:id/exercises/:workoutExerciseId``
   Remove an exercise block (and its sets) from the workout.

``POST /api/workout-exercises/:id/sets``
   Add a set to an exercise block, pre-filled by copying the previous
   set's values per :ref:`features/workout_logging:The active workout screen`.
   Body may override any field.

``PATCH /api/sets/:id``
   Update a set (weight, reps, duration, distance, flags, or
   ``completed``). Marking ``completed: true`` is what the client uses to
   trigger the rest timer client-side — the API itself is stateless with
   respect to the timer (see :doc:`../features/rest_timers`, which is
   entirely client-side state). It does have one server-side effect
   beyond saving the given fields: newly completing a set copies any of
   ``weight``/``reps``/``duration_seconds`` still null from that set's
   ``planned_*`` fields, then clears all of them, including
   ``planned_is_progressed`` (see :doc:`../data_flow`).

``DELETE /api/sets/:id``
   Remove a single set.

``GET /api/workouts/<id>/strength``
   Per-muscle strength against your usual, as described in
   :doc:`../features/strength_score`. Returns ``score`` (or ``null`` during the
   warm-up period) and ``muscles``, keyed by canonical slug, each with a
   ``status`` (``scored``, ``no_baseline``, or ``pending``), a ``ratio``,
   ``evidence``, and the body-map ``regions`` it lights up.

``GET /api/strength/history``
   The same per-muscle strength data for every completed workout, oldest
   first, computed in one pass rather than once per workout (see
   :doc:`../data_flow`). Each entry also carries ``workout_id``,
   ``started_at``/``date``, and ``template_id``. Backs the home screen's
   strength-over-time chart.
