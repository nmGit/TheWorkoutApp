"""Environment-driven configuration (12-factor style, see docs/architecture)."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "..", "data", "workout.db")
DEFAULT_CATALOG_DB_PATH = os.path.join(BASE_DIR, "..", "data", "catalog.db")


class Config:
    # The user's own data: workouts, templates, custom exercises, settings, body weight. This
    # is the database a future per-user split multiplies -- each user gets their own copy of
    # this one, all sharing the single CATALOG_DATABASE_URL below. See docs/data_model.rst
    # "Database split".
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.abspath(DEFAULT_DB_PATH)}"
    )
    # The shared exercise catalog: every non-custom ExerciseTemplate, plus the Muscle/
    # ExerciseMuscle/MuscleGroup reference data those rows link to. Vendored, not user-authored
    # -- rebuilt from the bundled datasets by scripts/seed_exercise_templates.py, never hand-
    # migrated with Alembic (see that script and models/exercise_template.py's bind key). Never
    # keyed by user, so every user (once there is more than one) reads the same one.
    SQLALCHEMY_BINDS = {
        "catalog": os.environ.get(
            "CATALOG_DATABASE_URL", f"sqlite:///{os.path.abspath(DEFAULT_CATALOG_DB_PATH)}"
        )
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")

    PORT = int(os.environ.get("PORT", "8000"))

    FRONTEND_DIST_DIR = os.environ.get(
        "FRONTEND_DIST_DIR",
        os.path.abspath(os.path.join(BASE_DIR, "..", "frontend", "dist")),
    )

    # Built Sphinx docs (see docs/, scripts/build-docs.sh), served at /docs by
    # app/routes/docs.py. Not built by default -- a missing directory is a 404,
    # not a startup failure.
    DOCS_BUILD_DIR = os.environ.get(
        "DOCS_BUILD_DIR",
        os.path.abspath(os.path.join(BASE_DIR, "..", "docs", "build", "html")),
    )

    # The two bundled exercise datasets, both git submodules at fixed
    # locations in this repo (so plain constants, not environment variables;
    # tests override them via a Config subclass). The "legacy" dataset is
    # hasaneyldrm/exercises-dataset; RepDB is the newer, preferred source for
    # images/text/muscles wherever it covers an exercise.
    EXERCISE_DATASET_DIR = os.path.abspath(
        os.path.join(BASE_DIR, "..", "external", "exercises-dataset")
    )
    REPDB_DATASET_DIR = os.path.abspath(
        os.path.join(BASE_DIR, "..", "external", "repdb-exercise-dataset")
    )
