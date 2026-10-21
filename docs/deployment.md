# Deployment

Prerequisites: AWS CLI v2 with credentials for the target account, and the skill created in the Alexa developer console (it gives you the skill ID).

## 1. Store the Gemini key (once)
Never put the key in the repo or a command line that lands in shell history.
```bash
read -rs KEY && aws ssm put-parameter --name /ask-gemini/api-key --type SecureString --value "$KEY" --region <region>; unset KEY
```
`read -rs` keeps the key out of shell history, but `--value "$KEY"` briefly shows it in the `aws` process arguments on a shared host. Where that matters, write it to a mode-600 temporary file and pass `file://` instead (check the CLI syntax first). To rotate the key, run the same command with `--overwrite`; running Lambda containers keep the old key until they are recycled.

## 2. Deploy
```bash
export AWS_REGION=<region> ALEXA_SKILL_ID=<amzn1.ask.skill...>
./scripts/deploy.sh            # prints the plan only
./scripts/deploy.sh --apply    # builds, deploys, publishes a version, moves alias "live"
```
Optional variables: `FUNCTION_NAME`, `LAMBDA_PYTHON`, `LAMBDA_ARCH` (`x86_64` or `arm64`; the wheel platform follows it), `LOG_RETENTION_DAYS`, `GEMINI_API_KEY_PARAM`, `RESERVED_CONCURRENCY` (caps parallel invocations to limit Gemini spend; accounts need enough unreserved concurrency left).

The script validates every value against an allowlist, checks that the SSM parameter exists, invokes the new version once with a LaunchRequest before moving the alias (a broken package never goes live), and leaves the Alexa permission untouched when it already matches the skill ID. It cannot change the architecture of an existing function and aborts if it differs.

## 3. Connect the skill
Set the endpoint of the skill (default region) to the ARN printed by the script, ending in `:live`, and upload `skill-package/` with the ASK CLI or the console.

## Rollback
```bash
aws lambda list-versions-by-function --function-name ask-gemini-skill --query 'Versions[].Version'
aws lambda update-alias --function-name ask-gemini-skill --name live --function-version <previous>
```

## Notes
- Only the alias `live` may be invoked by Alexa. A skill endpoint that points at the unqualified function ARN will stop working, and the script only warns if the function has an older resource policy: review it with `aws lambda get-policy --function-name ask-gemini-skill` and remove stale statements by hand.
- Rolling back the alias restores the old code and environment variables, but not the IAM policy (the role is shared). Published versions are never pruned; delete old ones by hand.
- Do not enable DEBUG logging for `ask_sdk`, `httpx` or `google.genai`: it could write the question into CloudWatch.
- The first deploy must confirm the `python3.13` runtime, the `kms:Decrypt` condition and cold-start latency (the SSM read happens on the first request).
