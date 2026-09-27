"""Production entrypoint: serves the app via Waitress.

Run with:  python wsgi.py
Binds 0.0.0.0:$PORT (default 8000). See docs/architecture.rst for config.
"""
from waitress import serve

from app import create_app
from app.config import Config

app = create_app()

if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=Config.PORT)
