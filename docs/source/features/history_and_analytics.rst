History & analytics
======================

Turning logged sets into "am I progressing" answers, without any manual
bookkeeping beyond normal set logging.

Workout history
-----------------

``/history`` — reverse-chronological list of completed workouts (one row:
date, name/template subtitle, exercise count). Total volume for a session
is shown on the detail view rather than in the list row, since it needs
per-set unit conversion that isn't worth doing for every row of a list.
Filterable by date range and by template. Tapping a row opens
``/history/:workoutId``, a
read-only-by-default rendering of that workout's exercise blocks and sets
(editable in place — see :doc:`workout_logging`), plus any PRs set that
day highlighted inline next to the set that earned them.

A lightweight calendar/heatmap view (like GitHub's contribution graph,
scoped to workout days) gives an at-a-glance sense of consistency and is
shown at the top of the history list.

Per-exercise progress
------------------------

On each :doc:`exercise_library`'s detail screen:

- **Chart**: a line chart of a selectable metric over time —
  ``max weight``, ``estimated 1RM``, or ``volume`` (per-workout sum of
  weight × reps) for ``weight_reps``/``bodyweight_reps`` exercises; for
  ``cardio`` exercises, distance or pace over time instead. Date range
  selectable (last 3/6/12 months, all time).
- **Personal records** card: heaviest weight, best estimated 1RM, best
  single-set volume, each with the date achieved (see
  :ref:`data_model:Business rules` for the exact definitions/formula).

These are computed by the backend on request (``GET
/api/exercises/:id/stats``, see :doc:`../api/stats`) rather than
maintained incrementally, since the query is cheap at single-user data
volumes and computing on read means there's no PR-cache to invalidate
correctly.

Dashboard
---------

``/`` (home) surfaces, above the fold: the current active workout if one
exists (with a one-tap "Continue" back into it — see
:ref:`features/workout_logging:Starting a workout`), the current workout
streak (consecutive weeks with >=1 workout), and any PRs from the last 7
days. Below that, a brief **recent workouts** list (last 4, name + date +
exercise count, linking to that workout's detail) with a "View all
history" link down to the full :doc:`history_and_analytics` list. The
home screen's job is still to get the user into a workout fast and give
an at-a-glance sense of "where am I" — the recent-workouts list is
deliberately short (4 rows) rather than a second full history page.
