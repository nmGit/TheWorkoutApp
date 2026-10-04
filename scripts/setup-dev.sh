#!/usr/bin/env bash
# Install / update everything WorkoutApp needs, then start the development
# servers with live reload:
#
#     ./scripts/setup-dev.sh
#
# Step 1 is exactly scripts/setup-everything.sh (system packages, git pull and
# datasets, Node, venv, database migration, exercise seed, frontend install and
# build) run with --no-start. Then it starts:
#   - the Flask API with its debug reloader   http://localhost:8000
#   - the Vite dev server (hot reload)        http://localhost:5173  <- open this
#
# Edit a React/TS file and the browser updates instantly; edit a Python file and
# the API restarts itself. Ctrl+C stops both servers.
#
# Options:
#   -h, --help    show this help
#   Everything else is passed through to setup-everything.sh, e.g.
#     --fresh --no-pull --update-datasets --db PATH --database-url URL --config FILE
#   (--port is ignored here: the dev servers always use 8000 and 5173.)

set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
LOCAL_NODE_BIN="$FRONTEND/.tools/node/bin"

if [ -t 1 ]; then BOLD=$'\033[1m' GREEN=$'\033[32m' RED=$'\033[31m' OFF=$'\033[0m'
else BOLD="" GREEN="" RED="" OFF=""; fi
step() { printf '\n%s==> %s%s\n' "$BOLD" "$*" "$OFF"; }
ok()   { printf '%s✓ %s%s\n' "$GREEN" "$*" "$OFF"; }
die()  { printf '%s✗ %s%s\n' "$RED" "$*" "$OFF" >&2; exit 1; }

port_in_use() {  # is something already listening on 127.0.0.1:$1 ?
  (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

# Everything is inside main() so a `git pull` run by setup-everything.sh that
# updates this file can't break the run mid-way.
main() {
  case "${1:-}" in
    -h|--help) sed -n '2,/^set -E/p' "${BASH_SOURCE[0]}" | sed '$d' | sed 's/^# \{0,1\}//'; exit 0 ;;
  esac

  # Resolve the settings (--db, --database-url, --config, PORT) in this shell, the
  # same way setup-everything.sh does, so the dev servers below use the database
  # that was just migrated. Exports made in the child process below don't reach us.
  # shellcheck disable=SC1091
  source "$ROOT/scripts/setup-everything.sh"
  parse_args "$@"
  apply_config
  show_config

  step "Setting up everything (scripts/setup-everything.sh --no-start)"
  "$ROOT/scripts/setup-everything.sh" --no-start "$@"

  step "Starting development servers"
  port_in_use 8000 && die "Port 8000 is already in use (maybe the production server). Stop it first: kill \$(cat data/server.pid)"
  port_in_use 5173 && die "Port 5173 is already in use (another Vite dev server?). Stop it first."
  [ -x "$LOCAL_NODE_BIN/node" ] && export PATH="$LOCAL_NODE_BIN:$PATH"

  # On exit (including Ctrl+C), kill this script's process group: both servers
  # below and their children (npm -> vite, Flask's reloader) share it.
  trap 'echo; echo "Stopping..."; kill 0 2>/dev/null' EXIT

  (
    cd "$BACKEND"
    # shellcheck disable=SC1091
    source .venv/bin/activate
    exec python3 run_dev.py
  ) &

  (
    cd "$FRONTEND"
    exec npm run dev
  ) &

  printf '\n%sReady.%s Open http://localhost:5173 (also reachable from other devices on this network).\n' "$BOLD" "$OFF"
  echo "API: http://localhost:8000.  Edits to frontend and backend code reload automatically. Press Ctrl+C to stop."

  # Exit as soon as either server stops, so a crash doesn't leave half the app running.
  wait -n
}

main "$@"
