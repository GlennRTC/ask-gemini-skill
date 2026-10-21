#!/usr/bin/env bash
# init.sh -- prepares the dev environment and runs a basic verification.
# Stack: Python 3 on AWS Lambda (Alexa custom skill + Gemini). No database in v1.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== init.sh: checking toolchain =="
command -v python3 >/dev/null || { echo "python3 not found" >&2; exit 1; }
python3 - <<'PY'
import sys
assert sys.version_info >= (3, 10), f"Python >= 3.10 required, found {sys.version.split()[0]}"
PY

echo "== init.sh: virtualenv and dependencies =="
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
if [ -f requirements.txt ]; then
  pip install --quiet -r requirements.txt
else
  echo "requirements.txt not present yet (no dependencies approved), skipping install"
fi

echo "== init.sh: secrets check =="
# The key is referenced by name only; its value is never printed.
if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "GEMINI_API_KEY is not set: real-API checks will be skipped (mocked checks still run)"
fi

echo "== init.sh: unit tests =="
if [ -d tests ]; then
  python3 -m unittest discover -s tests
else
  echo "tests/ not present yet (no feature implemented), skipping"
fi

echo "== init.sh: end-to-end smoke test =="
if [ -x scripts/smoke.sh ]; then
  ./scripts/smoke.sh
else
  echo "scripts/smoke.sh not present yet (feature F010), skipping"
fi

echo "== init.sh: environment ready =="
