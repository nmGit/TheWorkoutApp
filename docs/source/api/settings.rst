Settings & body weight
========================

``GET /api/settings``
   Returns the singleton ``UserSettings`` row.

``PATCH /api/settings``
   Partial update. ``weight_unit``, ``distance_unit``, ``theme`` (each
   validated against their fixed enum), ``default_rest_seconds``;
   ``progression_method`` (``double``/``linear``/``off``), ``experience``
   (``novice``/``intermediate``), ``load_step_lb``/``load_step_kg``
   (number, ``0 < x <= 100``), ``default_rep_range`` (a string that must
   parse, e.g. ``"8-12"``) — see :doc:`../features/progressive_overload`.
   Returns ``400`` naming the invalid field on any validation failure.

``GET /api/bodyweight``
   List body weight entries, most recent first. Query params: date range.

``POST /api/bodyweight``
   Upsert today's (or a given ``recorded_at``) entry — one entry per day,
   so posting again for the same date overwrites it rather than erroring.

``DELETE /api/bodyweight/:id``
   Remove an entry.
