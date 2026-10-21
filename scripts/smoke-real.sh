#!/usr/bin/env bash
# smoke-real.sh -- runs the smoke test against the real Gemini API without leaving the key
# in shell history, argv or the environment of your login shell.
set -euo pipefail

cd "$(dirname "$0")/.."

read -rsp "Gemini API key (input hidden): " GEMINI_API_KEY
echo
[ -n "$GEMINI_API_KEY" ] || { echo "empty key" >&2; exit 1; }
export GEMINI_API_KEY

./scripts/smoke.sh --real
