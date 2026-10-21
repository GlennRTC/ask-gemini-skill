#!/usr/bin/env bash
# package.sh -- builds build/lambda.zip with Linux wheels for the Lambda runtime.
# Uses manylinux wheels, so it works from any host OS. boto3 is provided by Lambda.
set -euo pipefail

cd "$(dirname "$0")/.."

LAMBDA_PYTHON="${LAMBDA_PYTHON:-3.13}"
LAMBDA_PLATFORM="${LAMBDA_PLATFORM:-manylinux2014_x86_64}"   # manylinux2014_aarch64 for arm64
PIP=python3
[ -x .venv/bin/python ] && PIP=.venv/bin/python

rm -rf build/lambda
mkdir -p build/lambda

"$PIP" -m pip install --quiet --no-compile --platform "$LAMBDA_PLATFORM" --implementation cp \
  --python-version "$LAMBDA_PYTHON" --only-binary=:all: --target build/lambda -r requirements.txt
# Only .py files: nothing else in skill/ (such as a stray .env) may reach the zip.
mkdir build/lambda/skill
cp skill/*.py build/lambda/skill/
find build/lambda -name __pycache__ -type d -prune -exec rm -rf {} +

rm -f build/lambda.zip
(cd build/lambda && python3 -m zipfile -c ../lambda.zip .)

echo "built build/lambda.zip ($(du -h build/lambda.zip | cut -f1)), python ${LAMBDA_PYTHON}, ${LAMBDA_PLATFORM}"
