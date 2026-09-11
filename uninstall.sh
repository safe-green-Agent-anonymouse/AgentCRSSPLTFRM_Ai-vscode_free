#!/usr/bin/env bash
# Desinstalle proprement Expert Dev Autopilot Console (Linux/macOS).
# Usage: ./uninstall.sh [--dry-run] [--yes] [--keep-config] [--keep-logs] [--keep-venv]
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

PY="python3"
[ -x ".venv/bin/python" ] && PY=".venv/bin/python"

"$PY" -m edac uninstall "$@"
code=$?

if [ -d ".venv" ] && [ "$code" -eq 0 ]; then
  echo "[edac] suppression finale de .venv"
  rm -rf .venv
fi

exit "$code"
