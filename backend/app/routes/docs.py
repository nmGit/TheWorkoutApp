"""Serves the built Sphinx documentation (see docs/) at /docs/*.

This is deliberately not under /api: it's static HTML, not JSON, and the
frontend links straight to it (e.g. ``/docs/features/workout_logging.html``)
so "Help" links work the same way in dev (via the Vite proxy) and in
production (served by this same Flask process, right next to the SPA).

The docs are built separately (``scripts/build-docs.sh``) rather than at
app startup: building needs Sphinx and its theme installed, which the
runtime app doesn't otherwise depend on, and a missing build should be a
calm 404 (see below), not a crash.
"""
import os

from flask import Blueprint, current_app, send_from_directory

bp = Blueprint("docs", __name__)


@bp.route("/docs", defaults={"path": ""})
@bp.route("/docs/", defaults={"path": ""})
@bp.route("/docs/<path:path>")
def serve_docs(path: str):
    docs_dir = current_app.config["DOCS_BUILD_DIR"]
    if not os.path.isdir(docs_dir):
        return {"error": "Docs aren't built yet; run scripts/build-docs.sh"}, 404

    full_path = os.path.join(docs_dir, path) if path else docs_dir
    if os.path.isdir(full_path):
        return send_from_directory(full_path, "index.html")
    if os.path.isfile(full_path):
        return send_from_directory(docs_dir, path)
    return {"error": "Not found"}, 404
