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
   Body weight series for the trend sparkline/chart. Query param
   ``range`` as above.
