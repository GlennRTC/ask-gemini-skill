# ADR-001: Gemini client via the google-genai SDK
**Fecha:** 2026-10-20
**Estado:** aceptado

**Contexto:**
F003 needs to call Google Gemini from the Lambda handler. The call must time out before Alexa's ~8 s limit and map failures to distinct errors.

**Decisión:**
Use the official `google-genai` SDK, pinned to 2.32.0 (Apache-2.0) in `requirements.txt` along with its transitive dependencies. Timeout is set through `HttpOptions(timeout=...)` (6 s default). The SDK is wrapped in `skill/gemini.py`, which exposes `ask_gemini` and `GeminiError(kind)`. The model name defaults to `gemini-2.5-flash` and can be overridden with `GEMINI_MODEL`.

**Alternativas consideradas:**
- Direct HTTP with `requests`/`httpx` — fewer dependencies, but we would own auth, request shape, error mapping and API changes.

**Consecuencias:**
- Less code and maintained error types; the SDK is the Google-supported path.
- Heavier package (pydantic, google-auth, cryptography, httpx): Lambda packaging must use manylinux wheels for the Lambda architecture (F011), and the zip grows.
- The default model name could not be verified in this session without an API key; confirm it before release.

**Referencias:** F003, user approval on 2026-10-20.
