Architecture
============

System shape
------------

.. code-block:: text

   ┌─────────────────────┐        HTTP/JSON        ┌──────────────────────────┐
   │  React SPA (Vite)   │ ───────────────────────► │  Flask app (REST API)    │
   │  served as static   │ ◄─────────────────────── │  served by Waitress WSGI │
   │  files in prod      │                          │                          │
   └─────────────────────┘                          └───────────┬──────────────┘
                                                                  │ SQLAlchemy
                                                                  ▼
                                                       ┌──────────────────────┐
                                                       │ SQLite (dev/default) │
                                                       │ or Postgres (prod)   │
                                                       └──────────────────────┘

In development, Vite's dev server runs on its own port with a proxy to the
Flask API (``/api/*``), giving hot-module-reload for the frontend. In
production, ``npm run build`` emits static assets that Flask serves
directly, so the whole app is a single Waitress process plus one database
file — deliberately simple to host.

``external/exercises-dataset`` is a git submodule
(https://github.com/hasaneyldrm/exercises-dataset) vendored at the repo
root: the source of the built-in exercise template library (name,
body part/equipment, English step-by-step instructions, and a thumbnail
image per exercise). It never touches application code directly — the
backend reads it only through ``scripts/seed_exercise_templates.py``,
which imports it into the ``exercise_templates`` table, and through the
``/api/exercise-templates/<id>/image`` route, which streams a thumbnail
straight out of the checkout. Clone with
``git clone --recurse-submodules``, or run
``git submodule update --init --recursive`` after a plain clone.

Backend layout
---------------

.. code-block:: text

   backend/
     app/
       __init__.py       # create_app() application factory
       config.py         # env-driven config (DATABASE_URL, CORS, etc.)
       extensions.py     # db = SQLAlchemy(), migrate = Migrate()
       models/           # SQLAlchemy ORM models (see data_model.rst)
       routes/           # Flask blueprints, one per resource
       serializers.py    # model -> JSON dict helpers
       services/         # business logic: 1RM estimation, PR detection,
                          # streak calculation, unit conversion
     migrations/          # Alembic migration scripts (Flask-Migrate)
     scripts/
       import_ods.py             # retired one-off importer for the legacy spreadsheet
       import_strong_csv.py      # ongoing importer, re-run per fresh Strong export
       backfill_workout_names.py # one-off: real names/timestamps for spreadsheet-era workouts
       seed_exercises.py         # seeds the built-in exercise library
       seed_exercise_templates.py # imports external/exercises-dataset into exercise_templates
       ods_parser.py             # spreadsheet cell-format parsing, used by import_ods.py
     tests/
     wsgi.py              # Waitress entrypoint (production)
     run_dev.py           # Flask dev server entrypoint (development)
   external/
     exercises-dataset/   # git submodule: exercise template data + images

The API is versionless (``/api/...``) since it is a first-party API for
this app's own frontend, not a public integration surface. All endpoints
return JSON; all mutating endpoints accept JSON bodies.

Frontend layout
-----------------

.. code-block:: text

   frontend/
     src/
       api/              # typed fetch wrappers + TanStack Query hooks per resource
       components/        # shared UI: RestTimer, SetRow, ExercisePicker, Nav, charts
       pages/              # one component per route
       context/            # SettingsContext (units, rest timer defaults)
       types.ts             # shared TS types mirroring API payloads
       main.tsx, App.tsx

Routing (React Router), by page — see :doc:`features/index` for behavior:

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Route
     - Page
   * - ``/``
     - Home / dashboard: start-workout CTA, active workout banner if one is
       in progress, recent PRs.
   * - ``/workout/active``
     - The in-progress workout logging screen.
   * - ``/templates``
     - Template list.
   * - ``/templates/:id``
     - Template editor.
   * - ``/history``
     - Workout history list.
   * - ``/history/:workoutId``
     - Read-only detail of a completed workout.
   * - ``/exercises``
     - Exercise library browser.
   * - ``/exercises/:id``
     - Exercise detail: history + progress chart for that exercise.
   * - ``/settings``
     - Units, rest timer defaults, body weight log.

Configuration
-------------

Backend configuration is environment-variable driven (12-factor style):

.. list-table::
   :widths: 30 20 50
   :header-rows: 1

   * - Variable
     - Default
     - Purpose
   * - ``DATABASE_URL``
     - ``sqlite:///../data/workout.db``
     - SQLAlchemy connection string. Point at Postgres in production by
       setting e.g. ``postgresql+psycopg://user:pass@host/db``.
   * - ``FLASK_ENV`` / ``FLASK_DEBUG``
     - unset (production)
     - Standard Flask debug toggle for local dev only.
   * - ``CORS_ORIGINS``
     - ``http://localhost:5173``
     - Allowed origins for the Vite dev server. Not needed in production
       since the SPA is served same-origin by Flask/Waitress.
   * - ``PORT``
     - ``8000``
     - Port Waitress binds to.
   * - ``EXERCISE_DATASET_DIR``
     - ``../external/exercises-dataset``
     - Path to the exercises-dataset submodule checkout, read by
       ``seed_exercise_templates.py`` and the template image route.

Deployment is intentionally left to the user (per project scope) — the app
just needs to run ``python wsgi.py`` (or any WSGI-compatible process
manager pointed at ``wsgi:app``) behind whatever reverse proxy/TLS
termination they choose, with a persisted volume for the SQLite file (or an
external Postgres instance).
