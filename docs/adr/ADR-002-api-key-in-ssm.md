# ADR-002: Gemini API key in SSM Parameter Store
**Fecha:** 2026-10-20
**Estado:** aceptado

**Contexto:**
F004 requires the API key to live outside the repo, logs and code, be cheap, and be loaded once per Lambda container.

**Decisión:**
Store the key as an SSM `SecureString` parameter. The Lambda receives only the parameter name in `GEMINI_API_KEY_PARAM` and reads it with `WithDecryption=True` on the first request, caching it in memory (`skill/secrets.py`). For local development `GEMINI_API_KEY` takes precedence. Errors never include the key or client messages. The Lambda role gets only `ssm:GetParameter` on that parameter (plus `kms:Decrypt` if a customer-managed key is used), defined in F011.

**Alternativas consideradas:**
- AWS Secrets Manager — adds per-secret monthly cost and rotation features this skill does not need.
- Plain Lambda environment variable — visible in the console and to anyone with read access to the function configuration.

**Consecuencias:**
- No extra cost for standard parameters; IAM scoped to one parameter.
- `boto3` is imported lazily and is provided by the Lambda runtime, so it is not in `requirements.txt`; running the SSM path locally needs `boto3` installed.
- No automatic rotation: replacing the key means updating the parameter and waiting for containers to recycle.

**Referencias:** F004, user approval on 2026-10-20.
