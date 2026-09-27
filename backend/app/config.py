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

    # Bundled exercises-dataset submodule (external/exercises-dataset), the
    # source of built-in exercise templates and their images.
    EXERCISE_DATASET_DIR = os.environ.get(
        "EXERCISE_DATASET_DIR",
        os.path.abspath(os.path.join(BASE_DIR, "..", "external", "exercises-dataset")),
    )
