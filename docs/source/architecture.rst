Architecture
============

System shape
------------

.. mermaid::

   flowchart LR
       A["React SPA (Vite)<br/>served as static files in prod"]
       B["Flask app (REST API)<br/>served by Waitress WSGI"]
       C["SQLite (dev/default)<br/>or Postgres (prod)"]
       A -- "HTTP/JSON" --> B
       B -- "HTTP/JSON" --> A
       B -- SQLAlchemy --> C

In development, Vite's dev server runs on its own port with a proxy to the
Flask API (``/api/*``), giving hot-module-reload for the frontend. In
production, ``npm run build`` emits static assets that Flask serves
directly, so the whole app is a single Waitress process plus one database
file — deliberately simple to host.

Two git submodules under ``external/`` are the source of the built-in
exercise library; neither is ever committed into this repo (RepDB's license
forbids redistributing its dataset, and the original's images are
© Gym visual):

- ``external/repdb-exercise-dataset`` (https://github.com/RepDB/exercise-dataset,
  "RepDB", 609 exercises): illustrations (two poses per exercise), step-by-step
  instructions, tips, difficulty, primary/secondary muscles, and highlighted
  muscle diagrams. Preferred wherever it covers an exercise.
- ``external/exercises-dataset`` (https://github.com/hasaneyldrm/exercises-dataset,
  1,324 exercises): the original source — name, body part/equipment, English
  instructions, one thumbnail each. Stays as the fallback for everything RepDB
  doesn't cover.

They never touch application code directly: the backend reads them only
through ``scripts/seed_exercise_templates.py``, which imports both into the
``exercise_templates`` table, and through the
``/api/exercise-templates/<id>/image[/<n>]`` and ``/api/muscles/<slug>/image``
routes, which stream images straight out of the checkouts. Their locations are
fixed attributes of ``Config`` (``EXERCISE_DATASET_DIR``, ``REPDB_DATASET_DIR``)
rather than environment variables, since they live at a known place in the
repo. Clone with ``git clone --recurse-submodules``, or run
``git submodule update --init --recursive`` after a plain clone.

Backend layout
---------------

.. code-block:: text

   backend/
     app/
       __init__.py       # create_app() application factory
       config.py         # env-driven config (DATABASE_URL, CORS, DOCS_BUILD_DIR, etc.)
       extensions.py     # db = SQLAlchemy(), migrate = Migrate()
       models/           # SQLAlchemy ORM models (see data_model.rst)
       routes/           # Flask blueprints, one per resource (see below)
       serializers.py    # model -> JSON dict helpers
       services/         # business logic (see below)
     migrations/          # Alembic migration scripts (Flask-Migrate)
     scripts/
       import_strong_csv.py      # ongoing importer, re-run per fresh Strong export
       backfill_workout_names.py # one-off: real names/timestamps for spreadsheet-era workouts
       seed_exercise_templates.py # imports both external/ datasets into exercise_templates (idempotent, --dry-run)
       ods_parser.py             # spreadsheet cell-format parsing (shared with import_strong_csv.py)
     tests/
     wsgi.py              # Waitress entrypoint (production)
     run_dev.py           # Flask dev server entrypoint (development)
   docs/
     source/              # this manual (Sphinx + MyST + Furo)
     requirements.txt      # Sphinx and its extensions/theme
     build/html/           # generated; served at /docs by app/routes/docs.py
   scripts/
     setup-everything.sh       # install/update everything (venv, deps, DB, build, docs) and start production
     setup.env.example         # template for the script's optional setup.env (port, database location)
     build-docs.sh              # build docs/source -> docs/build/html (own venv, see "Documentation" below)
   external/
     exercises-dataset/        # git submodule: the original exercise dataset (fallback)
     repdb-exercise-dataset/   # git submodule: RepDB (preferred where it covers an exercise)

The API is versionless (``/api/...``) since it is a first-party API for
this app's own frontend, not a public integration surface. All endpoints
return JSON; all mutating endpoints accept JSON bodies. ``/docs/*`` is the
one non-JSON, non-SPA route — static HTML (see "Documentation" below).

``app/routes/`` blueprints, by resource:

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Module
     - Mounts
   * - ``workouts.py``
     - Workouts, sets, strength scoring, generated workouts
       (``/workouts``, ``/sets``, ``/workout-exercises``)
   * - ``templates.py``
     - Templates and their exercises (``/templates``)
   * - ``exercise_templates.py``
     - The exercise catalog, muscle groups, muscle recency, images
       (``/exercise-templates``, ``/muscle-groups``, ``/muscles``)
   * - ``settings.py``
     - Settings and the body-weight log (``/settings``, ``/bodyweight``)
   * - ``stats.py``
     - Per-exercise stats/PRs, dashboard, body-weight series (``/stats``,
       ``/exercises/:id/stats``)
   * - ``docs.py``
     - The built documentation (``/docs``) — see "Documentation" below

``app/services/``, where the actual logic lives (routes stay thin):

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Module
     - Responsibility
   * - ``strength.py``
     - Shared pieces of strength scoring: muscle shares, e1RM, which sets
       count. Also the retired first-generation score method, kept for
       comparison (``scripts/evaluate_generated.py``).
   * - ``generated_v2.py``
     - The live strength-scoring method: per-exercise baselines, outlier
       rejection, shrinkage. See :doc:`features/strength_score` and
       :doc:`data_flow`.
   * - ``recency.py``
     - The single place "days since this muscle was last trained" is
       computed, from completed workouts.
   * - ``generate.py``
     - Generated-workout exercise selection: training-group ranking and
       the alternating pick. See :doc:`features/generated_workouts`.
   * - ``sets_plan.py``
     - Builds a template-started or generated workout's planned sets,
       applying progressive overload to the working sets. See
       :doc:`features/progressive_overload`.
   * - ``muscle_catalog.py``
     - Resolves a dataset's raw muscle wording to a canonical ``Muscle``
       slug (used only when seeding/editing exercises' muscles).
   * - ``muscle_regions.py``
     - Maps a canonical muscle slug to the body-map SVG region(s) it
       lights up. Not stored in the database.
   * - ``stats.py``
     - PRs, progress series, the dashboard, body-weight series.
   * - ``units.py`` / ``dates.py``
     - Weight/distance conversion; local-date handling for history grouping.

Frontend layout
-----------------

.. code-block:: text

   frontend/
     src/
       api/              # typed fetch wrappers + TanStack Query hooks per resource
       components/        # shared UI: RestTimer, SetRow, ExercisePicker, Nav,
                          # MuscleMap (musclemap-js wrapper), GenerateWorkout,
                          # BodyweightLog, PlanSets, charts
       pages/              # one component per route (Settings.tsx exports
                          # several: the menu plus each section page)
       context/            # SettingsContext (units, theme, progression
                          # defaults), UndoContext (deferred-delete snackbar),
                          # RestTimerContext
       lib/                # format.ts, units.ts, strengthColors.ts, recency.ts
       types.ts             # shared TS types mirroring API payloads
       main.tsx, App.tsx

The body-map SVG itself is rendered by ``@abdofallah/musclemap-js``
(pinned to a fixed commit, not a tagged release), wrapped by
``components/MuscleMap.tsx``; ``lib/strengthColors.ts`` and
``lib/recency.ts`` turn a strength ratio or a recency day-count into the
fill colours it's given.

Routing (React Router), by page — see :doc:`features/index` for behavior:

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Route
     - Page
   * - ``/``
     - Home / dashboard: start-workout CTA (blank, from template, or
       generated), active workout banner if one is in progress, muscle
       recency map, strength-over-time chart, recent workouts, body
       weight log/chart, streak, recent PRs.
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
     - A menu of three section pages (``SettingsMenuPage``, in
       ``pages/Settings.tsx``).
   * - ``/settings/general``
     - Units, theme, default rest timer.
   * - ``/settings/generated-workouts``
     - Progressive overload: progression method, rep range, experience,
       load step.
   * - ``/settings/about``
     - Exercise data sources' attribution.
   * - ``/docs/*``
     - Not a React route — served directly by the Flask backend (see
       "Documentation" below), outside the SPA.

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
   * - ``DOCS_BUILD_DIR``
     - ``<repo>/docs/build/html``
     - Where ``app/routes/docs.py`` looks for built docs to serve at
       ``/docs``. A missing directory is a calm 404, not a startup
       failure — the app runs fine with no docs built.

``scripts/setup-everything.sh`` sets these for you: ``--port``, ``--db``/
``--database-url`` (or ``PORT``/``DATABASE_URL`` in the environment or a
``setup.env`` file; flags beat the environment, which beats the file).

Deployment is intentionally left to the user (per project scope) — the app
just needs to run ``python wsgi.py`` (or any WSGI-compatible process
manager pointed at ``wsgi:app``) behind whatever reverse proxy/TLS
termination they choose, with a persisted volume for the SQLite file (or an
external Postgres instance).

Documentation
-------------

This manual is built separately from the app (Sphinx isn't a runtime
dependency) and served by the same backend process that serves the API
and the SPA, so in-app links work the same way in every environment:

- **Building**: ``./scripts/build-docs.sh`` creates/reuses a dedicated
  venv at ``docs/.venv`` (installs ``docs/requirements.txt`` into it, kept
  separate from ``backend/.venv``), then runs
  ``sphinx-build -b html -W docs/source docs/build/html`` — ``-W`` turns a
  broken cross-reference (a stale ``:doc:``/``:ref:``) into a build
  failure rather than a silently broken link. ``--clean`` forces a full
  rebuild; ``--open`` opens the result in a browser.
  ``scripts/setup-everything.sh`` runs it too, as a non-fatal step (the
  app runs fine without docs built, and a transient install failure
  shouldn't block everything else).
- **Serving**: ``app/routes/docs.py`` serves ``docs/build/html`` at
  ``/docs/*`` — not under ``/api``, since it's static HTML, not JSON.
  Dev: the Vite dev server proxies ``/docs`` to the Flask backend, the
  same way it already proxies ``/api``. Production: the same Waitress
  process serves it alongside the SPA and the API, no extra server.
- **Linking from the app**: pages link into specific sections of the
  :doc:`user manual <index>` — never the developer guide — via plain
  ``<a href="/docs/...">`` tags opened in a new tab, placed in
  ``PageTitle``'s ``action`` slot where that's free, or inline next to
  the control they explain otherwise. There's no dedicated "DocsLink"
  abstraction; it's just a URL to the already-built HTML, so a broken
  link is caught by ``sphinx-build -W`` (on the anchor's existence on the
  docs side; the frontend build doesn't check these URLs) rather than
  needing its own test.
