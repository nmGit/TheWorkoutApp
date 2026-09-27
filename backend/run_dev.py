"""Development entrypoint: Flask's debug server with auto-reload.

Run with:  python run_dev.py
The Vite dev server (frontend/) proxies /api/* here on port 8000.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=8000)
