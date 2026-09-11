#!/usr/bin/env bash
# Equivalent de run.bat pour Linux/macOS.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

PY="python3"
[ -x ".venv/bin/python" ] && PY=".venv/bin/python"

if ! "$PY" -c "import tkinter" 2>/dev/null; then
  echo "[edac] tkinter manquant : sudo apt install python3-tk (Debian/Ubuntu)" >&2
  exit 1
fi

exec "$PY" -m edac "$@"
