Overview
========

Goals
-----

WorkoutApp exists to answer, quickly and without friction, the four
questions a lifter asks around a workout:

1. **What am I doing today?** — start from a template or a blank workout.
2. **What did I just lift, and when do I go again?** — fast set logging with
   an automatic rest timer.
3. **What have I done before on this exercise?** — last time's weights/reps
   shown inline while logging, plus a full history.
4. **Am I actually progressing?** — per-exercise charts and personal
   records, built from logged data, not manual bookkeeping.

Everything else in the product is in service of those four questions. This
is a single-user, self-hosted tool first; multi-user support is a
non-goal for v1 (see :ref:`overview:Non-goals`).

Primary reference: Strong
--------------------------

`Strong <https://www.strong.app/>`_ is the reference UX for this project
because its core loop — pick a template, log sets against a rest timer,
review history — is the most refined version of this workflow in the
market. WorkoutApp adopts Strong's core interaction model:

- A workout is a flat list of **exercise blocks**, each containing an
  ordered list of **sets** (weight × reps, or duration/distance for
  cardio).
- Logging a set is a single tap once weight/reps are entered, and
  immediately starts the rest timer.
- Templates ("routines" in Strong) are just a saved shape for a workout:
  which exercises, in what order, with target sets/reps to pre-fill.
- The set-entry row always shows the previous performance for that
  exercise/slot so the lifter knows what to beat.

WorkoutApp does not attempt to clone Strong's subscription features
(coaching plans, workout plans marketplace, Apple Watch app). It focuses on
the free, core logging/template/history/timer loop plus the analytics that
loop enables.

Tech stack
----------

.. list-table::
   :widths: 20 30 50
   :header-rows: 1

   * - Layer
     - Choice
     - Why
   * - Frontend
     - React + Vite + TypeScript
     - Fast dev server, standard SPA tooling, typed API contracts shared
       conceptually with the backend schemas.
   * - Styling
     - Tailwind CSS
     - Utility-first styling keeps a gym-usable (large touch targets, high
       contrast, one-handed) UI fast to build and consistent.
   * - Data fetching
     - TanStack Query
     - Caching, optimistic updates for set logging, background refetch on
       window focus (useful when switching apps mid-workout to check a
       phone timer, etc.).
   * - Charts
     - Recharts
     - Declarative React charts, sufficient for line/bar progress charts.
   * - Backend framework
     - Flask
     - WSGI framework, pairs directly with Waitress, minimal ceremony for a
       CRUD-and-aggregation API.
   * - Production server
     - Waitress
     - Pure-Python, production-grade WSGI server, no native build
       dependencies — required per project constraints.
   * - ORM / migrations
     - SQLAlchemy + Alembic (via Flask-Migrate)
     - Relational model with real joins (see :doc:`data_model`), versioned
       schema migrations from day one.
   * - Database
     - SQLite by default, Postgres-compatible
     - SQLite is zero-ops and plenty fast for a single-user self-hosted
       app; the schema avoids SQLite-incompatible features so switching
       ``DATABASE_URL`` to Postgres later is a config change, not a
       rewrite.

Non-goals
---------

Explicitly out of scope for v1, to keep the product coherent:

- Multi-user accounts, social features, sharing workouts.
- Nutrition/macro tracking.
- Wearable/device sync (Apple Watch, Garmin, etc.).
- Offline-first / PWA installability (may come later; not v1).
- AI-generated programming or coaching.

Body-weight tracking is **in scope** (see
:doc:`features/bodyweight_and_settings`) since it's low-cost, relational to
progress analytics (e.g. relative strength), and present in the source
workout history being imported.
