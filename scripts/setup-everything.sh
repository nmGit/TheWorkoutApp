#!/usr/bin/env bash
# Install / update everything WorkoutApp needs, then start the production server.
#
# Meant to be re-run any time ("clean reset"), e.g. on a Raspberry Pi:
#
#     ./scripts/setup-everything.sh
#
# Each run, in order:
#   1. installs missing system packages (git, curl, python3, python3-venv) via apt
#   2. pulls the latest code and brings both exercise-dataset git submodules
#      up to the commits this repo pins
#   3. makes sure a suitable Node.js is available (downloads the right build for
#      this machine's CPU into frontend/.tools/node if the system has none)
#   4. creates the backend virtualenv if needed and upgrades its dependencies
#   5. backs up the database (only if migrations are pending), then migrates it
#   6. seeds/refreshes the exercise catalog (safe to re-run; never touches
#      anything you've edited)
#   7. installs frontend dependencies from the lockfile and builds the web app
#   8. stops any previously started production server, then starts a new one
#
# Options:
#   --fresh              first delete backend/.venv and frontend/node_modules
#                        (a true from-scratch rebuild of every dependency)
#   --no-pull            don't `git pull`
#   --update-datasets    move the two dataset submodules to their *latest*
#                        upstream commits instead of the pinned ones
#   -d, --detach         run the server in the background (survives logout);
#                        log: data/server.log, pid: data/server.pid
#   --no-start           set everything up but don't start the server
#
# Configuration (each setting can come from a flag, an environment variable, or
# a config file; a flag beats the environment, which beats the file):
#   --port N               PORT                 port to serve on (default 8000)
#   --db PATH              (sets DATABASE_URL)  SQLite database file
#                                               (default: <repo>/data/workout.db)
#   --database-url URL     DATABASE_URL         full SQLAlchemy URL instead of --db
#   --config FILE          SETUP_CONFIG         KEY=VALUE file with any of the above
#                                               (default: <repo>/setup.env if present;
#                                               see scripts/setup.env.example)
#   NODE_VERSION           (env or config file) Node build to download if needed
#   -h, --help
#
#
# Everything is inside main() on purpose: bash reads a script as it runs, so
# without that a `git pull` that updates this very file could break the run.

set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
DATA_DIR="$ROOT/data"
VENV="$BACKEND/.venv"
PY="$VENV/bin/python"
LOCAL_NODE_DIR="$FRONTEND/.tools/node"
PID_FILE="$DATA_DIR/server.pid"
LOG_FILE="$DATA_DIR/server.log"

# Vite 8 needs Node >= 22.12 (or >= 20.19). This is what gets downloaded when
# the machine has no suitable Node.
MIN_PYTHON="3.10"
KEEP_BACKUPS=5

CONFIG_FILE="${SETUP_CONFIG:-}"
DO_PULL=1 FRESH=0 UPDATE_DATASETS=0 DETACH=0 START=1

if [ -t 1 ]; then BOLD=$'\033[1m' DIM=$'\033[2m' RED=$'\033[31m' GREEN=$'\033[32m' YELLOW=$'\033[33m' OFF=$'\033[0m'
else BOLD="" DIM="" RED="" GREEN="" YELLOW="" OFF=""; fi

step() { printf '\n%s==> %s%s\n' "$BOLD" "$*" "$OFF"; }
info() { printf '%s\n' "$*"; }
ok()   { printf '%s✓ %s%s\n' "$GREEN" "$*" "$OFF"; }
warn() { printf '%s! %s%s\n' "$YELLOW" "$*" "$OFF" >&2; }
die()  { printf '%s✗ %s%s\n' "$RED" "$*" "$OFF" >&2; exit 1; }

version_ge() { [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -n1)" = "$2" ]; }  # $1 >= $2

usage() { sed -n '2,/^# Everything is inside/p' "${BASH_SOURCE[0]}" | sed '$d' | sed 's/^# \{0,1\}//'; }

as_root() {
  if [ "$(id -u)" -eq 0 ]; then "$@"
  elif command -v sudo >/dev/null 2>&1; then sudo "$@"
  else die "Need root to install system packages but sudo isn't available. Run as root or install: $*"
  fi
}

apt_install() {
  command -v apt-get >/dev/null 2>&1 || die "Please install these yourself (no apt-get here): $*"
  as_root apt-get update -qq
  as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y "$@"
}

# ---------------------------------------------------------------- 1. system
ensure_system_packages() {
  step "System packages"
  [ "$(uname -s)" = "Linux" ] || warn "Not Linux ($(uname -s)): automatic package/Node install is Linux-only; continuing with what's installed."
  local missing=()
  command -v git  >/dev/null 2>&1 || missing+=(git)
  command -v curl >/dev/null 2>&1 || missing+=(curl ca-certificates)
  command -v python3 >/dev/null 2>&1 || missing+=(python3)
  if command -v python3 >/dev/null 2>&1 && ! python3 -c 'import venv, ensurepip' >/dev/null 2>&1; then
    missing+=(python3-venv)
  fi
  if [ "${#missing[@]}" -gt 0 ]; then
    info "Installing: ${missing[*]}"
    apt_install "${missing[@]}"
  fi
  python3 -c "import sys; sys.exit(0 if sys.version_info >= tuple(map(int, '$MIN_PYTHON'.split('.'))) else 1)" \
    || die "Python $MIN_PYTHON or newer is required (found $(python3 --version 2>&1))."
  ok "git, curl, $(python3 --version), venv support"
}

# ------------------------------------------------------------------- 2. git
update_source() {
  step "Source code and exercise datasets"
  if [ ! -d "$ROOT/.git" ]; then
    warn "Not a git checkout; skipping pull and submodules (the datasets must already be in external/)."
  else
    if [ "$DO_PULL" -eq 1 ]; then
      if git -C "$ROOT" rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
        if [ -n "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]; then
          warn "Uncommitted changes in the checkout; skipping git pull."
        else
          git -C "$ROOT" pull --ff-only || warn "git pull failed (diverged branch or no network?); continuing with the current code."
        fi
      else
        info "No upstream branch configured; skipping git pull."
      fi
    fi
    git -C "$ROOT" submodule sync --recursive >/dev/null
    # Shallow first (these are big); fall back to a full fetch if the server refuses.
    local remote_flag=()
    [ "$UPDATE_DATASETS" -eq 1 ] && remote_flag=(--remote)
    git -C "$ROOT" submodule update --init --recursive --depth 1 "${remote_flag[@]+"${remote_flag[@]}"}" \
      || git -C "$ROOT" submodule update --init --recursive "${remote_flag[@]+"${remote_flag[@]}"}"
  fi
  [ -f "$ROOT/external/exercises-dataset/data/exercises.json" ] \
    || die "external/exercises-dataset is missing. Run: git submodule update --init --recursive"
  [ -f "$ROOT/external/repdb-exercise-dataset/exercises.json" ] \
    || die "external/repdb-exercise-dataset is missing. Run: git submodule update --init --recursive"
  ok "Source up to date; both exercise datasets present"
}

# ------------------------------------------------------------------ 3. node
node_ok() {  # node_ok /path/to/node  -> usable for Vite 8?
  local v
  v="$("$1" -p 'process.versions.node' 2>/dev/null)" || return 1
  version_ge "$v" 22.12.0 || { [ "${v%%.*}" = "20" ] && version_ge "$v" 20.19.0; }
}

install_local_node() {
  [ "$(uname -s)" = "Linux" ] || die "Can't download Node automatically on $(uname -s). Install Node 22.12+ (or 20.19+) and re-run."
  local arch tarball base tmp
  case "$(uname -m)" in
    x86_64|amd64)   arch=x64 ;;
    aarch64|arm64)  arch=arm64 ;;
    armv7l|armv8l)  arch=armv7l ;;
    *) die "Unsupported CPU architecture for the Node download: $(uname -m)" ;;
  esac
  tarball="node-v${NODE_VERSION}-linux-${arch}.tar.gz"
  base="https://nodejs.org/dist/v${NODE_VERSION}"
  tmp="$(mktemp -d)"
  info "Downloading Node v${NODE_VERSION} (linux-${arch})..."
  curl -fSL --progress-bar "$base/$tarball" -o "$tmp/$tarball"
  curl -fsSL "$base/SHASUMS256.txt" -o "$tmp/SHASUMS256.txt"
  ( cd "$tmp" && grep " ${tarball}\$" SHASUMS256.txt | sha256sum -c - ) \
    || { rm -rf "$tmp"; die "Node download failed its checksum; not installing it."; }
  rm -rf "$LOCAL_NODE_DIR"
  mkdir -p "$(dirname "$LOCAL_NODE_DIR")"
  tar -xzf "$tmp/$tarball" -C "$tmp"
  mv "$tmp/node-v${NODE_VERSION}-linux-${arch}" "$LOCAL_NODE_DIR"
  rm -rf "$tmp"
}

ensure_node() {
  step "Node.js"
  local local_node="$LOCAL_NODE_DIR/bin/node" v
  if [ -x "$local_node" ] && node_ok "$local_node" \
     && version_ge "$("$local_node" -p 'process.versions.node')" "$NODE_VERSION"; then
    export PATH="$LOCAL_NODE_DIR/bin:$PATH"
  elif command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1 && node_ok "$(command -v node)"; then
    : # the system Node is new enough
  else
    install_local_node
    export PATH="$LOCAL_NODE_DIR/bin:$PATH"
  fi
  v="$(node -p 'process.versions.node')"
  ok "Node v$v ($(command -v node)), npm $(npm -v)"
}

# --------------------------------------------------------------- 4. backend
ensure_venv() {
  step "Backend virtualenv and Python dependencies"
  if [ "$FRESH" -eq 1 ] && [ -d "$VENV" ]; then
    info "--fresh: removing $VENV"
    rm -rf "$VENV"
  fi
  if [ -d "$VENV" ] && ! "$PY" -c 'import sys' >/dev/null 2>&1; then
    warn "Existing virtualenv is broken (different Python or CPU?); recreating it."
    rm -rf "$VENV"
  fi
  if [ ! -d "$VENV" ]; then
    info "Creating $VENV"
    python3 -m venv "$VENV"
  fi
  "$PY" -m pip install -q --upgrade --disable-pip-version-check --progress-bar off pip
  "$PY" -m pip install -q --upgrade --disable-pip-version-check --progress-bar off -r "$BACKEND/requirements.txt"
  "$PY" -c 'import flask, flask_sqlalchemy, flask_migrate, flask_cors, waitress' \
    || die "Backend dependencies didn't import cleanly after installing."
  ok "Python dependencies installed and up to date"
}

# ------------------------------------------------------------------- config
CONFIG_KEYS="PORT DATABASE_URL NODE_VERSION"

# Read KEY=VALUE lines (no shell evaluation) for the keys above, without
# overriding anything already set by a flag or the environment.
load_config_file() {
  local file="$1" line key value
  [ -f "$file" ] || die "Config file not found: $file"
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    case "$line" in ''|\#*) continue ;; esac
    line="${line#export }"
    key="${line%%=*}"; value="${line#*=}"
    key="${key//[[:space:]]/}"
    case " $CONFIG_KEYS " in *" $key "*) ;; *) warn "$file: ignoring unknown setting '$key'"; continue ;; esac
    value="${value#"${value%%[![:space:]]*}"}"; value="${value%"${value##*[![:space:]]}"}"
    case "$value" in \"*\") value="${value#\"}"; value="${value%\"}" ;; \'*\') value="${value#\'}"; value="${value%\'}" ;; esac
    [ -n "${!key+x}" ] || export "$key=$value"
  done <"$file"
  info "Read settings from $file"
}

apply_config() {
  if [ -z "$CONFIG_FILE" ] && [ -f "$ROOT/setup.env" ]; then CONFIG_FILE="$ROOT/setup.env"; fi
  [ -z "$CONFIG_FILE" ] || load_config_file "$CONFIG_FILE"
  export PORT="${PORT:-8000}"
  NODE_VERSION="${NODE_VERSION:-22.14.0}"
  case "$PORT" in ''|*[!0-9]*) die "PORT must be a number (got '$PORT')." ;; esac
  # DATABASE_URL is read by the backend itself (backend/app/config.py); only
  # export it when set, so an unset value keeps the default data/workout.db.
  if [ -n "${DATABASE_URL:-}" ]; then export DATABASE_URL; fi
}

show_config() {
  local db; db="$(sqlite_path)"
  info "Port:      $PORT"
  info "Database:  ${db:-$DATABASE_URL}"
}

# -------------------------------------------------------------- 5. database
sqlite_path() {  # prints the sqlite file in use, or nothing for a non-sqlite DATABASE_URL
  case "${DATABASE_URL:-}" in
    "") printf '%s\n' "$DATA_DIR/workout.db" ;;
    sqlite:////*) printf '%s\n' "${DATABASE_URL#sqlite:///}" ;;
    sqlite:///*) printf '%s\n' "$BACKEND/instance/${DATABASE_URL#sqlite:///}" ;;  # Flask-SQLAlchemy resolves relative paths there
    *) ;;
  esac
}

migrate_database() {
  step "Database"
  mkdir -p "$DATA_DIR"
  local db current head
  db="$(sqlite_path)"
  [ -z "$db" ] || mkdir -p "$(dirname "$db")"
  export FLASK_APP=wsgi.py
  cd "$BACKEND"

  head="$("$VENV/bin/flask" db heads 2>/dev/null | tail -n1 | awk '{print $1}')"
  current="$("$VENV/bin/flask" db current 2>/dev/null | tail -n1 | awk '{print $1}')" || current=""

  # The Exercise -> ExerciseTemplate merge dropped the old `exercises` table
  # and needed a hand-run data step first. A database still holding rows in it
  # must be brought up to date from a current copy, not by blindly upgrading.
  if [ -n "$db" ] && [ -s "$db" ] && "$PY" - "$db" <<'EOF'
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
has = c.execute("select 1 from sqlite_master where type='table' and name='exercises'").fetchone()
sys.exit(0 if has and c.execute("select count(*) from exercises").fetchone()[0] > 0 else 1)
EOF
  then
    die "$db still has the old 'exercises' table with data. Upgrading it automatically would lose history; copy over an up-to-date data/workout.db from your main machine instead."
  fi

  if [ "$current" = "$head" ] && [ -n "$head" ]; then
    ok "Database schema already current ($head)"
    return
  fi

  if [ -n "$db" ] && [ -s "$db" ]; then
    local backup="$(dirname "$db")/$(basename "$db").pre-setup-$(date +%Y%m%d-%H%M%S)-backup"
    cp -p "$db" "$backup"
    info "Backed up $db -> $backup"
    # keep only the newest few of these automatic backups
    ls -1t "$(dirname "$db")/$(basename "$db")".pre-setup-*-backup 2>/dev/null | tail -n +"$((KEEP_BACKUPS + 1))" | xargs -r rm -f --
  elif [ -z "$db" ]; then
    warn "DATABASE_URL isn't SQLite, so no automatic backup was made; make sure you have your own."
  fi
  "$VENV/bin/flask" db upgrade
  ok "Database migrated to ${head:-latest}"
}

seed_catalog() {
  step "Exercise catalog"
  local out
  out="$(mktemp)"
  if ! "$PY" scripts/seed_exercise_templates.py >"$out" 2>&1; then
    cat "$out" >&2; rm -f "$out"; die "Seeding the exercise catalog failed."
  fi
  sed -n '/^Totals/,$p' "$out"
  rm -f "$out"
  ok "Catalog seeded/refreshed (your own edits are never overwritten)"
}

# -------------------------------------------------------------- 6. frontend
build_frontend() {
  step "Frontend dependencies and build"
  cd "$FRONTEND"
  if [ "$FRESH" -eq 1 ] && [ -d node_modules ]; then
    info "--fresh: removing frontend/node_modules"
    rm -rf node_modules
  fi
  [ -f package-lock.json ] || die "frontend/package-lock.json is missing; can't do a reproducible install."
  npm ci --no-audit --no-fund
  # tsc + vite can want >1 GB; give them headroom on small boards.
  NODE_OPTIONS="${NODE_OPTIONS:---max-old-space-size=2048}" npm run build
  [ -f dist/index.html ] || die "Frontend build didn't produce dist/index.html."
  ok "Frontend built ($(du -sh dist | cut -f1))"
}

# --------------------------------------------------------------- 7. server
pid_is_ours() {  # a wsgi.py process started from this checkout's backend/
  local pid="$1"
  [ -r "/proc/$pid/cmdline" ] || return 1
  [ "$(readlink "/proc/$pid/cwd" 2>/dev/null)" = "$BACKEND" ] \
    && tr '\0' ' ' <"/proc/$pid/cmdline" | grep -q 'wsgi\.py'
}

stop_old_server() {
  local candidates="" pid
  [ -f "$PID_FILE" ] && candidates="$(cat "$PID_FILE" 2>/dev/null || true)"
  candidates="$candidates $(pgrep -f 'wsgi\.py' 2>/dev/null || true)"
  for pid in $(printf '%s\n' $candidates | sort -u); do
    pid_is_ours "$pid" || continue
    info "Stopping the previous server (pid $pid)..."
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 20); do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
    kill -0 "$pid" 2>/dev/null && { warn "It didn't stop; forcing."; kill -9 "$pid" 2>/dev/null || true; }
  done
  rm -f "$PID_FILE"
}

port_is_free() {
  "$PY" - "$PORT" <<'EOF'
import socket, sys
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind(("0.0.0.0", int(sys.argv[1])))
except OSError:
    sys.exit(1)
EOF
}

print_urls() {
  local ips ip
  printf '%sWorkoutApp is available at:%s\n' "$BOLD" "$OFF"
  printf '  http://localhost:%s\n' "$PORT"
  ips="$(hostname -I 2>/dev/null || true)"
  for ip in $ips; do printf '  http://%s:%s\n' "$ip" "$PORT"; done
}

start_server() {
  step "Production server"
  stop_old_server
  port_is_free || die "Port $PORT is in use by something other than this app's server. Free it or use --port <other>."
  cd "$BACKEND"
  export PORT
  if [ "$DETACH" -eq 1 ]; then
    mkdir -p "$DATA_DIR"
    setsid nohup "$PY" wsgi.py >>"$LOG_FILE" 2>&1 < /dev/null &
    echo $! >"$PID_FILE"
    local up=0
    for _ in $(seq 1 30); do
      if curl -fsS -o /dev/null "http://127.0.0.1:$PORT/api/settings" 2>/dev/null; then up=1; break; fi
      kill -0 "$(cat "$PID_FILE")" 2>/dev/null || break
      sleep 0.5
    done
    if [ "$up" -ne 1 ]; then tail -n 30 "$LOG_FILE" >&2 || true; die "The server didn't come up. Log: $LOG_FILE"; fi
    ok "Server running in the background (pid $(cat "$PID_FILE"))"
    print_urls
    info "${DIM}Log: $LOG_FILE   Stop: kill \$(cat $PID_FILE)${OFF}"
  else
    print_urls
    info "${DIM}Press Ctrl+C to stop.${OFF}"
    exec "$PY" wsgi.py
  fi
}

# --------------------------------------------------------------------- main
parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --fresh) FRESH=1 ;;
      --no-pull) DO_PULL=0 ;;
      --update-datasets) UPDATE_DATASETS=1 ;;
      -d|--detach) DETACH=1 ;;
      --no-start) START=0 ;;
      --port) [ $# -ge 2 ] || die "--port needs a value"; export PORT="$2"; shift ;;
      --db) [ $# -ge 2 ] || die "--db needs a path"; export DATABASE_URL="sqlite:///$(realpath -m -- "$2")"; shift ;;
      --database-url) [ $# -ge 2 ] || die "--database-url needs a value"; export DATABASE_URL="$2"; shift ;;
      --config) [ $# -ge 2 ] || die "--config needs a path"; CONFIG_FILE="$(realpath -m -- "$2")"; shift ;;
      -h|--help) usage; exit 0 ;;
      *) die "Unknown option: $1 (see --help)" ;;
    esac
    shift
  done
}

main() {
  parse_args "$@"

  trap 'printf "%s✗ Setup stopped at line %s; see the output above. Fix it and re-run -- this script is safe to repeat.%s\n" "$RED" "$LINENO" "$OFF" >&2' ERR

  printf '%sWorkoutApp setup%s  (%s)\n' "$BOLD" "$OFF" "$ROOT"
  apply_config
  show_config
  ensure_system_packages
  update_source
  ensure_node
  ensure_venv
  migrate_database
  seed_catalog
  build_frontend
  if [ "$START" -eq 1 ]; then
    start_server
  else
    step "Done"
    ok "Everything is installed and up to date (server not started: --no-start)."
  fi
}

# Only run when executed directly; scripts/setup-dev.sh sources this file to
# reuse the config functions (parse_args, apply_config).
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
  exit $?
fi
