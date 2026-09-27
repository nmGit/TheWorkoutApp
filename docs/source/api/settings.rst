Settings & body weight
========================

``GET /api/settings``
   Returns the singleton ``UserSettings`` row.

``PATCH /api/settings``
   Partial update (``weight_unit``, ``distance_unit``,
   ``default_rest_seconds``, ``theme``).

``GET /api/bodyweight``
   List body weight entries, most recent first. Query params: date range.

``POST /api/bodyweight``
   Upsert today's (or a given ``recorded_at``) entry — one entry per day,
   so posting again for the same date overwrites it rather than erroring.

``DELETE /api/bodyweight/:id``
   Remove an entry.
