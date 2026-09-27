"""Application factory for the WorkoutApp Flask backend."""
import os

from flask import Flask, send_from_directory

from app.config import Config
from app.extensions import cors, db, migrate


def create_app(config_object: type[Config] = Config) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, origins=app.config["CORS_ORIGINS"])

    from app import models as _models  # noqa: F401  (registers ORM metadata for create_all/migrate)
    from app.routes import register_routes

    register_routes(app)

    _register_settings_bootstrap(app)
    _register_frontend_static(app)

    return app


def _register_settings_bootstrap(app: Flask) -> None:
    """Ensure the singleton UserSettings row exists before the first request."""
    from app.models.settings import UserSettings

    @app.before_request
    def _ensure_settings():  # pragma: no cover - trivial
        UserSettings.get()


def _register_frontend_static(app: Flask) -> None:
    """Serve the built React SPA (frontend/dist) if it exists.

    In development the Vite dev server handles the frontend and this is a
    no-op (the directory won't exist yet). In production, `npm run build`
    populates frontend/dist and Waitress serves it from this same process.
    """
    dist_dir = app.config["FRONTEND_DIST_DIR"]

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def spa(path):  # pragma: no cover - static file serving
        if path.startswith("api/"):
            return {"error": "not found"}, 404
        if not os.path.isdir(dist_dir):
            return {"error": "frontend not built; run `npm run build` in frontend/"}, 404
        full_path = os.path.join(dist_dir, path)
        if path and os.path.isfile(full_path):
            return send_from_directory(dist_dir, path)
        return send_from_directory(dist_dir, "index.html")
