#!/usr/bin/env bash
# smoke.sh -- local end-to-end check. Pass --real to also call the real Gemini API.
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON=python3
[ -x .venv/bin/python ] && PYTHON=.venv/bin/python
"$PYTHON" scripts/smoke.py "$@"
