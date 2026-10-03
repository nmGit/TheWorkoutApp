"""Development entrypoint: Flask's debug server with auto-reload.

Run with:  python run_dev.py
The Vite dev server (frontend/) proxies /api/* here on port 8000.
Binds 0.0.0.0 so it's reachable from other devices on the network, same as
the production entrypoint (wsgi.py).
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
