#!/usr/bin/env bash
# deploy.sh -- idempotent deploy of the Lambda behind the Alexa skill.
# Without --apply it only prints what it would do. The SSM parameter with the Gemini key is
# created by hand (see docs/deployment.md); this script never sees the key value.
set -euo pipefail

cd "$(dirname "$0")/.."

die() { echo "error: $*" >&2; exit 1; }

: "${ALEXA_SKILL_ID:?set ALEXA_SKILL_ID to the skill id (amzn1.ask.skill....)}"
AWS_REGION="${AWS_REGION:?set AWS_REGION}"
FUNCTION_NAME="${FUNCTION_NAME:-voice-assistant-skill}"
ROLE_NAME="${ROLE_NAME:-${FUNCTION_NAME}-role}"
KEY_PARAM="${GEMINI_API_KEY_PARAM:-/ask-gemini/api-key}"
LAMBDA_PYTHON="${LAMBDA_PYTHON:-3.13}"
LAMBDA_ARCH="${LAMBDA_ARCH:-x86_64}"
LOG_RETENTION_DAYS="${LOG_RETENTION_DAYS:-14}"
RESERVED_CONCURRENCY="${RESERVED_CONCURRENCY:-}"   # optional cap on parallel invocations
HANDLER="skill.lambda_function.lambda_handler"
ALIAS="live"

# Strict allowlists: these values end up in sed, JSON and the IAM policy resource.
[[ $AWS_REGION =~ ^[a-z]{2}(-[a-z]+)+-[0-9]+$ ]] || die "bad AWS_REGION"
[[ $ALEXA_SKILL_ID =~ ^amzn1\.ask\.skill\.[A-Za-z0-9._-]+$ ]] || die "bad ALEXA_SKILL_ID"
[[ $KEY_PARAM =~ ^/[A-Za-z0-9_./-]+$ ]] || die "GEMINI_API_KEY_PARAM must start with / and use [A-Za-z0-9_./-]"
[[ $FUNCTION_NAME =~ ^[A-Za-z0-9_-]{1,64}$ ]] || die "bad FUNCTION_NAME"
[[ $ROLE_NAME =~ ^[A-Za-z0-9_-]{1,64}$ ]] || die "bad ROLE_NAME"
[[ $LAMBDA_PYTHON =~ ^3\.[0-9]+$ ]] || die "bad LAMBDA_PYTHON"
[[ $LOG_RETENTION_DAYS =~ ^[0-9]+$ ]] || die "bad LOG_RETENTION_DAYS"
[[ -z $RESERVED_CONCURRENCY || $RESERVED_CONCURRENCY =~ ^[0-9]+$ ]] || die "bad RESERVED_CONCURRENCY"

# One variable decides the architecture; the wheel platform is derived from it.
case "$LAMBDA_ARCH" in
  x86_64) export LAMBDA_PLATFORM=manylinux2014_x86_64 ;;
  arm64) export LAMBDA_PLATFORM=manylinux2014_aarch64 ;;
  *) die "LAMBDA_ARCH must be x86_64 or arm64" ;;
esac
export LAMBDA_PYTHON

APPLY=0
[ "${1:-}" = "--apply" ] && APPLY=1

if [ "$APPLY" -eq 0 ]; then
  cat <<PLAN
Plan (re-run with --apply to execute), region ${AWS_REGION}:
  1. check that SSM parameter ${KEY_PARAM} exists
  2. build the package (scripts/package.sh, ${LAMBDA_PLATFORM})
  3. create/update IAM role ${ROLE_NAME}: read ${KEY_PARAM} only, write its own logs
  4. create the log group with ${LOG_RETENTION_DAYS} days of retention
  5. create/update Lambda ${FUNCTION_NAME} (python${LAMBDA_PYTHON}, ${LAMBDA_ARCH}), env ALEXA_SKILL_ID, GEMINI_API_KEY_PARAM
  6. publish a version and invoke it once with a LaunchRequest; abort if it fails
  7. point alias '${ALIAS}' at it
  8. allow only skill ${ALEXA_SKILL_ID} to invoke ${FUNCTION_NAME}:${ALIAS}
Use the printed ARN ending in :${ALIAS} as the skill endpoint.
PLAN
  exit 0
fi

command -v aws >/dev/null || die "aws CLI not found"
export AWS_DEFAULT_REGION="$AWS_REGION"

# Succeeds if the resource exists, fails (1) only on "not found", aborts on any other error.
exists() {
  local out
  if out="$("$@" 2>&1)"; then return 0; fi
  if grep -qE 'ResourceNotFoundException|NoSuchEntity|ParameterNotFound' <<<"$out"; then return 1; fi
  echo "$out" >&2
  exit 1
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

exists aws ssm get-parameter --name "$KEY_PARAM" >/dev/null \
  || die "SSM parameter ${KEY_PARAM} not found; create it first (docs/deployment.md)"

./scripts/package.sh

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
sed -e "s|__REGION__|${AWS_REGION}|g" -e "s|__ACCOUNT_ID__|${ACCOUNT_ID}|g" \
  -e "s|__KEY_PARAM__|${KEY_PARAM}|g" -e "s|__FUNCTION_NAME__|${FUNCTION_NAME}|g" \
  infra/role-policy.json > "$TMP/role-policy.json"
KEY_PARAM="$KEY_PARAM" python3 - "$TMP/env.json" <<'PY'
import json, os, sys
env = {"ALEXA_SKILL_ID": os.environ["ALEXA_SKILL_ID"], "GEMINI_API_KEY_PARAM": os.environ["KEY_PARAM"]}
json.dump({"Variables": env}, open(sys.argv[1], "w"))
PY

if ! exists aws iam get-role --role-name "$ROLE_NAME" >/dev/null; then
  aws iam create-role --role-name "$ROLE_NAME" \
    --assume-role-policy-document "file://infra/trust-policy.json" >/dev/null
  echo "created role ${ROLE_NAME}; waiting for IAM propagation"
  sleep 10
fi
aws iam put-role-policy --role-name "$ROLE_NAME" --policy-name "${FUNCTION_NAME}-access" \
  --policy-document "file://${TMP}/role-policy.json"
ROLE_ARN="$(aws iam get-role --role-name "$ROLE_NAME" --query Role.Arn --output text)"

# The log group exists, with retention, before any code can write to it.
LOG_GROUP="/aws/lambda/${FUNCTION_NAME}"
EXISTING_GROUP="$(aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" \
  --query "logGroups[?logGroupName=='${LOG_GROUP}'].logGroupName | [0]" --output text)"
if [ "$EXISTING_GROUP" != "$LOG_GROUP" ]; then
  aws logs create-log-group --log-group-name "$LOG_GROUP"
fi
aws logs put-retention-policy --log-group-name "$LOG_GROUP" --retention-in-days "$LOG_RETENTION_DAYS"

if exists aws lambda get-function --function-name "$FUNCTION_NAME" >/dev/null; then
  CURRENT_ARCH="$(aws lambda get-function-configuration --function-name "$FUNCTION_NAME" \
    --query 'Architectures[0]' --output text)"
  [ "$CURRENT_ARCH" = "$LAMBDA_ARCH" ] \
    || die "function architecture is ${CURRENT_ARCH}, requested ${LAMBDA_ARCH}; Lambda cannot change it in place"
  aws lambda update-function-code --function-name "$FUNCTION_NAME" \
    --zip-file fileb://build/lambda.zip >/dev/null
  aws lambda wait function-updated --function-name "$FUNCTION_NAME"
  aws lambda update-function-configuration --function-name "$FUNCTION_NAME" \
    --role "$ROLE_ARN" --runtime "python${LAMBDA_PYTHON}" --handler "$HANDLER" \
    --timeout 10 --memory-size 256 --environment "file://${TMP}/env.json" >/dev/null
else
  aws lambda create-function --function-name "$FUNCTION_NAME" --role "$ROLE_ARN" \
    --runtime "python${LAMBDA_PYTHON}" --architectures "$LAMBDA_ARCH" --handler "$HANDLER" \
    --timeout 10 --memory-size 256 --environment "file://${TMP}/env.json" \
    --zip-file fileb://build/lambda.zip >/dev/null
fi
aws lambda wait function-updated --function-name "$FUNCTION_NAME"

if [ -n "$RESERVED_CONCURRENCY" ]; then
  aws lambda put-function-concurrency --function-name "$FUNCTION_NAME" \
    --reserved-concurrent-executions "$RESERVED_CONCURRENCY" >/dev/null
fi

VERSION="$(aws lambda publish-version --function-name "$FUNCTION_NAME" --query Version --output text)"

# Invoke the new version before it goes live: catches import errors and architecture mismatches.
python3 - "$TMP/launch.json" <<'PY'
import json, os, sys
app = {"applicationId": os.environ["ALEXA_SKILL_ID"]}
user = {"userId": "amzn1.ask.account.deploy-check"}
json.dump({"version": "1.0",
           "session": {"new": True, "sessionId": "amzn1.echo-api.session.deploy-check", "application": app, "user": user},
           "context": {"System": {"application": app, "user": user}},
           "request": {"type": "LaunchRequest", "requestId": "amzn1.echo-api.request.deploy-check",
                       "timestamp": "2026-01-01T00:00:00Z", "locale": "en-US"}}, open(sys.argv[1], "w"))
PY
FN_ERROR="$(aws lambda invoke --function-name "${FUNCTION_NAME}:${VERSION}" \
  --cli-binary-format raw-in-base64-out --payload "file://${TMP}/launch.json" \
  --query FunctionError --output text "$TMP/response.json")"
if [ "$FN_ERROR" != "None" ] || ! grep -q outputSpeech "$TMP/response.json"; then
  die "version ${VERSION} failed its launch check (alias not moved); inspect the CloudWatch logs"
fi

if exists aws lambda get-alias --function-name "$FUNCTION_NAME" --name "$ALIAS" >/dev/null; then
  aws lambda update-alias --function-name "$FUNCTION_NAME" --name "$ALIAS" \
    --function-version "$VERSION" >/dev/null
else
  aws lambda create-alias --function-name "$FUNCTION_NAME" --name "$ALIAS" \
    --function-version "$VERSION" >/dev/null
fi

# Keep the permission untouched when it already carries this skill ID, so there is no gap.
POLICY_JSON="$(aws lambda get-policy --function-name "$FUNCTION_NAME" --qualifier "$ALIAS" \
  --query Policy --output text 2>/dev/null || true)"
if ! python3 -c '
import json, sys
doc = json.loads(sys.argv[1] or "{}")
ok = any(s.get("Sid") == "alexa-skill"
         and s.get("Condition", {}).get("StringEquals", {}).get("lambda:EventSourceToken") == sys.argv[2]
         for s in doc.get("Statement", []))
sys.exit(0 if ok else 1)' "$POLICY_JSON" "$ALEXA_SKILL_ID"; then
  if [ -n "$POLICY_JSON" ]; then
    aws lambda remove-permission --function-name "$FUNCTION_NAME" --qualifier "$ALIAS" \
      --statement-id alexa-skill >/dev/null
  fi
  aws lambda add-permission --function-name "$FUNCTION_NAME" --qualifier "$ALIAS" \
    --statement-id alexa-skill --action lambda:InvokeFunction --principal alexa-appkit.amazon.com \
    --event-source-token "$ALEXA_SKILL_ID" >/dev/null
fi

if exists aws lambda get-policy --function-name "$FUNCTION_NAME" >/dev/null; then
  echo "warning: the unqualified function ${FUNCTION_NAME} has its own resource policy; review it:" >&2
  echo "  aws lambda get-policy --function-name ${FUNCTION_NAME}" >&2
fi

echo "deployed version ${VERSION}. Skill endpoint ARN:"
echo "arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}:${ALIAS}"
