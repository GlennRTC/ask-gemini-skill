#!/usr/bin/env bash
# verify.sh -- the project's verification command. Run locally (via init.sh) and in CI.
# Expects the dependencies from requirements-dev.txt to be installed.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== verify: unit tests =="
python3 -m unittest discover -s tests

echo "== verify: dependency audit =="
pip-audit -r requirements.txt
