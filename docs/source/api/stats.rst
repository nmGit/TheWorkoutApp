Stats
=====

``GET /api/exercises/:id/stats``
   Query params: ``metric`` (``max_weight``/``est_1rm``/``volume``/
   ``distance``/``pace``, default depends on ``tracking_type``), ``range``
   (``3m``/``6m``/``12m``/``all``, default ``all``).

   Response::

      {
        "exercise_id": 12,
        "metric": "est_1rm",
        "series": [{"date": "2024-01-05", "value": 185.5, "workout_id": 44}, ...],
        "personal_records": {
          "max_weight": {"value": 225, "date": "2024-08-02", "workout_id": 90},
          "est_1rm": {"value": 231.2, "date": "2024-08-02", "workout_id": 90},
          "best_set_volume": {"value": 1800, "date": "2024-06-10", "workout_id": 71}
        }
      }

   All values computed per :ref:`data_model:Business rules` (Epley
   formula for ``est_1rm``, warmup sets excluded). ``cardio``-type
   exercises instead return ``longest_distance``/``fastest_pace`` in
   ``personal_records``.

``GET /api/stats/dashboard``
   Powers the home screen: ``{active_workout_id, current_streak_weeks,
   recent_prs: [...]}``, where ``recent_prs`` covers the last 7 days
   across all exercises.

``GET /api/stats/bodyweight``
   Body weight series. Query param ``range`` as above. Currently unused
   by the frontend — the home dashboard's body-weight chart
   (:doc:`../features/bodyweight_and_settings`) builds its points
   client-side from ``GET /api/bodyweight``'s raw entries instead, so
   every entry (not just this endpoint's range) is available to delete
   from the same view. A candidate for removal, or for the chart to
   switch to it if server-side range filtering turns out to matter.
