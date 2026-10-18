# WorkoutApp

A self-hosted strength-training tracker — rest timers, workout logging,
reusable templates, and progress analytics, built React + Vite on the
front end and Flask + Waitress on the back end. See
[`docs/`](docs/source/index.rst) (Sphinx) for the full product and
engineering documentation; this project was built docs-first, so that's
the source of truth for intended behavior.

## Stack

- **Frontend**: React + Vite + TypeScript, Tailwind CSS, TanStack Query, Recharts, React Router
- **Backend**: Flask + SQLAlchemy + Alembic (Flask-Migrate), served by Waitress in production
- **Database**: SQLite by default (`data/workout.db`), Postgres-compatible via `DATABASE_URL`
- **Exercises**: the catalog combines two datasets, both git submodules (nothing from
  them is committed here):
  [RepDB](https://repdb.co) at `external/repdb-exercise-dataset` — illustrations,
  instructions, tips and muscle diagrams (free tier; **Exercise data by
  [RepDB (repdb.co)](https://repdb.co)**, attribution required by its license) —
  and the original [exercises-dataset](https://github.com/hasaneyldrm/exercises-dataset)
  at `external/exercises-dataset` (data/instructions MIT-licensed; images © Gym visual —
  keep the `© Gym visual — https://gymvisual.com/` attribution intact wherever they're
  shown). RepDB's content is used wherever it covers an exercise; the original is the
  fallback everywhere else.

## First-time setup

```bash
# Clone with both exercise-dataset submodules (or run
# `git submodule update --init --recursive` after a plain clone)
git clone --recurse-submodules <this-repo-url>

# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=wsgi.py
flask db upgrade                            # creates data/workout.db
python3 scripts/seed_exercise_templates.py  # seeds muscle groups + the exercise catalog from external/*-dataset
                                            # (add --dry-run first to see what it would do; safe to re-run)

# Frontend
cd ../frontend
npm install
```

### One command (Raspberry Pi / any server)

```bash
./scripts/setup-everything.sh            # install/update everything, then run the production server
./scripts/setup-everything.sh --detach   # same, but keep it running in the background
```

Safe to re-run any time as a "clean reset": it installs missing system packages,
pulls the latest code, updates the dataset submodules, creates the Python venv and
upgrades its packages, installs a suitable Node.js if needed, backs up and migrates
the database, re-seeds the exercise catalog, rebuilds the frontend and restarts the
server on `$PORT` (default 8000). `--fresh` also rebuilds the venv and `node_modules`
from scratch; `--help` lists the rest. Settings can be passed as flags
(`--port 8080`, `--db /path/to/workout.db`, `--database-url ...`), environment
variables (`PORT`, `DATABASE_URL`), or a config file: copy
[`scripts/setup.env.example`](scripts/setup.env.example) to `setup.env` (git-ignored,
picked up automatically) or point at one with `--config FILE`. Flags beat the
environment, which beats the file. By default the database is `data/workout.db`. Your `data/workout.db` is not in git, so copy
it to the Pi's `data/` folder first if you want your history there.

## Running in development

```bash
# Terminal 1 - API on :8000
cd backend && source .venv/bin/activate && python3 run_dev.py

# Terminal 2 - Vite dev server on :5173 (proxies /api to :8000)
cd frontend && npm run dev
```

Open http://localhost:5173.

Or do the setup and start both dev servers in one go (same setup as
`setup-everything.sh`, then the API and Vite with live reload; Ctrl+C stops both):

```bash
./scripts/setup-dev.sh          # add --fresh / --no-pull / etc. as with setup-everything.sh
```

## Running in production

```bash
cd frontend && npm run build          # emits frontend/dist
cd ../backend && source .venv/bin/activate
python3 wsgi.py                       # Waitress, serves API + built SPA on :8000
```

Point `DATABASE_URL` at Postgres for production if you don't want SQLite;
everything else is a single process behind whatever reverse proxy/TLS
termination you choose (hosting itself is out of scope for this repo).

## Tests

```bash
cd backend && source .venv/bin/activate && python3 -m pytest
```

## Docs

```bash
cd docs
pip install -r requirements.txt
make html      # docs/build/html/index.html
```
