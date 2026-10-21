# ADR-003: Deploy the Lambda with AWS CLI scripts and a versioned alias
**Fecha:** 2026-10-21
**Estado:** propuesto

**Contexto:**
F011 needs a repeatable, idempotent deployment of the Lambda, a least-privilege role, a trigger restricted to the skill ID and a rollback path. Neither the AWS CLI, SAM nor the ASK CLI is installed in the development environment, so none of the options below could be run here.

**Decisión:**
Use `scripts/package.sh` (manylinux wheels, stdlib `zipfile`) and `scripts/deploy.sh` (AWS CLI v2 only). Every deploy publishes a Lambda version and moves the alias `live`; the Alexa endpoint is the ARN ending in `:live`, and the invoke permission is restricted with `--event-source-token` to `ALEXA_SKILL_ID`. The role policy is in `infra/role-policy.json` (one exact SSM parameter, kms:Decrypt only via SSM, logs of its own group). The new version is invoked once before the alias moves. Log retention is set to 14 days (the group is created before the function). Rollback is `aws lambda update-alias` to a previous version. The Alexa skill package (`skill-package/`) is uploaded separately, with the ASK CLI or the developer console.

**Alternativas consideradas:**
- AWS SAM / CloudFormation — declarative and diffable, but adds a new tool and a stack to manage for a single function.
- ASK CLI `deploy` — deploys skill and Lambda together, but hides IAM details and cannot restrict the trigger as precisely.

**Consecuencias:**
- No new Python dependency; only the AWS CLI is needed.
- Bash scripts own idempotency by hand (get-or-create), which is less robust than a CloudFormation stack and drift is not detected.
- The runtime (`python3.13`) and the `kms:Decrypt` condition for the AWS-managed SSM key are written from knowledge, not verified against a real account; the first deploy must confirm them.
- Nothing in this repo has been deployed yet.

**Referencias:** F011, ADR-002.
