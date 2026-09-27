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

## First-time setup

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=wsgi.py
flask db upgrade                        # creates data/workout.db
python3 scripts/seed_exercises.py       # seeds muscle groups + exercise library

# Optional: import legacy workout history from a .ods spreadsheet
pip install -r scripts/requirements.txt
python3 scripts/import_ods.py /path/to/Weightlifting.ods

# Frontend
cd ../frontend
npm install
```

## Running in development

```bash
# Terminal 1 - API on :8000
cd backend && source .venv/bin/activate && python3 run_dev.py

# Terminal 2 - Vite dev server on :5173 (proxies /api to :8000)
cd frontend && npm run dev
```

Open http://localhost:5173.

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
