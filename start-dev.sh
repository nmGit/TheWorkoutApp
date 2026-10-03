#!/usr/bin/env bash
# Starts the WorkoutApp backend (Flask dev server, :8000) and frontend
# (Vite dev server, :5173) together. Ctrl+C stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# On exit (including Ctrl+C), kill everything in this script's process
# group -- that's the script itself plus both background jobs below (and
# their children, e.g. npm's vite child), since none of them start their
# own process group.
trap 'echo; echo "Stopping..."; kill 0 2>/dev/null' EXIT

echo "Starting backend  (http://localhost:8000, also reachable via this machine's LAN IP) ..."
(
  cd "$ROOT/backend"
  source .venv/bin/activate
  exec python3 run_dev.py
) &

echo "Starting frontend (http://localhost:5173, also reachable via this machine's LAN IP) ..."
(
  cd "$ROOT/frontend"
  export PATH="$PWD/.tools/node/bin:$PATH"
  exec npm run dev
) &

echo
echo "Both servers running (bound to 0.0.0.0 -- reachable from other devices on the network too). Press Ctrl+C to stop both."
wait
