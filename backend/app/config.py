"""Environment-driven configuration (12-factor style, see docs/architecture)."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "..", "data", "workout.db")


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.abspath(DEFAULT_DB_PATH)}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")

    PORT = int(os.environ.get("PORT", "8000"))

    FRONTEND_DIST_DIR = os.environ.get(
        "FRONTEND_DIST_DIR",
        os.path.abspath(os.path.join(BASE_DIR, "..", "frontend", "dist")),
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
