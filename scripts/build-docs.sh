#!/usr/bin/env bash
# Build the Sphinx documentation (docs/source) into static HTML:
#
#     ./scripts/build-docs.sh
#
# Creates/reuses a dedicated virtualenv at docs/.venv (kept separate from
# backend/.venv since Sphinx and its theme aren't a runtime dependency of the
# app itself), installs docs/requirements.txt into it, then runs
# ``sphinx-build``. Output lands in docs/build/html, which is what
# backend/app/routes/docs.py serves at /docs/* -- run this (or
# scripts/setup-everything.sh, which calls it) before relying on in-app
# "Help" links, and again after editing anything under docs/source.
#
# Options:
#   -h, --help     show this help
#   --clean        remove docs/build first (full rebuild, not incremental)
#   --open         open the built docs in a browser when done

set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
DOCS="$ROOT/docs"
VENV="$DOCS/.venv"

if [ -t 1 ]; then BOLD=$'\033[1m' GREEN=$'\033[32m' OFF=$'\033[0m'
else BOLD="" GREEN="" OFF=""; fi
step() { printf '\n%s==> %s%s\n' "$BOLD" "$*" "$OFF"; }
ok()   { printf '%s✓ %s%s\n' "$GREEN" "$*" "$OFF"; }

CLEAN=0
OPEN=0
for arg in "$@"; do
  case "$arg" in
    -h|--help) grep '^#' "$0" | sed '1d;s/^# \{0,1\}//'; exit 0 ;;
    --clean) CLEAN=1 ;;
    --open) OPEN=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

main() {
  step "Setting up docs/.venv"
  if [ ! -x "$VENV/bin/python" ]; then
    python3 -m venv "$VENV"
  fi
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet -r "$DOCS/requirements.txt"
  ok "docs/.venv ready"

  if [ "$CLEAN" = 1 ]; then
    step "Removing docs/build"
    rm -rf "$DOCS/build"
  fi

  step "Building HTML docs"
  # -W: a bad :ref:/:doc: link (stale cross-reference) fails the build instead
  # of silently shipping a broken link, since that's the whole point of these
  # docs staying accurate.
  "$VENV/bin/sphinx-build" -b html -W --keep-going "$DOCS/source" "$DOCS/build/html"
  ok "Built docs/build/html/index.html"

  echo
  echo "Served at /docs when the Flask backend is running (dev: via the Vite"
  echo "proxy on :5173; prod: the same process serving the SPA)."

  if [ "$OPEN" = 1 ]; then
    python3 -m webbrowser "file://$DOCS/build/html/index.html" || true
  fi
}

main
