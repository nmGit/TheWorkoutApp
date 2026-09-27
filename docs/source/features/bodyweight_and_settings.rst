Body weight & settings
========================

Body weight log
------------------

A simple date + weight log, independent of workouts (``BodyweightEntry``,
one entry per day). Accessible from Settings and from the home dashboard
as a small trend sparkline. Included in v1 because the source workout
history already contains a body-weight-adjacent signal (a ``Body`` /
``Stretching`` column) and because relative-strength context (e.g. "your
squat is now 1.5x bodyweight") is a natural, low-cost extension once both
numbers exist — computed the same on-read way as other stats, not stored.

Settings
--------

``/settings`` holds the single ``UserSettings`` row:

- **Units**: weight (lbs/kg) and distance (mi/km). Changes the *display*
  and the unit new entries are recorded in; never rewrites historical
  values (see :ref:`data_model:Business rules`).
- **Default rest timer** duration, used when an exercise has no
  per-exercise override.
- **Theme**: system/light/dark.

There is no account/profile section — v1 is single-user with no auth (see
:ref:`overview:Non-goals`), so Settings is purely app preferences.
