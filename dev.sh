#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-20100}"
SKIP_INSTALL="${SKIP_INSTALL:-0}"
SKIP_MIGRATE="${SKIP_MIGRATE:-0}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: Python not found: $PYTHON_BIN" >&2
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment: $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

if [ "$SKIP_INSTALL" != "1" ]; then
  echo "Installing dependencies from requirements.txt"
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
fi

if [ "$SKIP_MIGRATE" != "1" ]; then
  echo "Applying migrations"
  python manage.py migrate
fi

echo "Starting Django dev server at http://${HOST}:${PORT}"
exec python manage.py runserver "${HOST}:${PORT}"
