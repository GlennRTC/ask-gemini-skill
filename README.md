# Ada, an Alexa voice assistant skill

An Alexa custom skill that takes a spoken question, sends it to Google Gemini and reads the answer back. Runs as a Python 3 AWS Lambda function.

```
"Alexa, open assistant ada" -> "Hi, what would you like to know?"
"who wrote Don Quixote"     -> Alexa speaks Gemini's answer, then asks if you want another question
```

- **Locales:** es-US, es-ES, en-US (invocation names "asistente ada" and "assistant ada", provisional).
- **Short-term context:** the last few turns of the current session are replayed to the model so follow-ups work ("and when was he born?"). They live only in Alexa's session attributes: the skill has no database and nothing survives the session.
- **Privacy:** logs hold only locale, answer length, latency and error type, never the question or the answer. See `docs/privacy-policy.md` (draft).

## How it works

1. `AskGeminiIntent` receives the question in an `AMAZON.SearchQuery` slot.
2. `skill/gemini.py` calls Gemini (SDK `google-genai`) with a short-voice system prompt, safety filters, a 500-character input cap, a 300-token output cap and a 4.5 s client-side timeout (Alexa gives up at about 8 s).
3. `skill/speech.py` strips markdown and URLs, truncates at a sentence boundary and escapes SSML.
4. Failures (timeout, quota, blocked content, API error) get distinct spoken messages.
5. Voice: every response is spoken with an Amazon Polly voice per locale (`skill/voice.py`: es-US Miguel, es-ES Enrique, en-US Matthew; an empty value keeps Alexa's voice).
6. Guardrails (`skill/guardrails.py`): questions about suicide, self-harm or overdose get a fixed emergency message and never reach the model; health questions (doses, medication, symptoms) add a prompt rule against personal dosing or diagnosis plus a spoken disclaimer. They are keyword lists, so paraphrases can slip through.

## Layout

```
skill/                  Lambda code (lambda_function.py, gemini.py, secrets.py, speech.py)
skill-package/          Alexa manifest and interaction models per locale
tests/                  unittest suite
scripts/                init.sh, verify.sh, smoke.sh / smoke.py
docs/                   ADRs, privacy policy draft, certification notes
requirements.txt        Runtime dependencies (pinned)
requirements-dev.txt    Adds pip-audit
```

## Configuration

| Variable | Purpose |
|---|---|
| `ALEXA_SKILL_ID` | Required. Requests from any other skill are rejected. |
| `GEMINI_API_KEY_PARAM` | Name of the SSM SecureString parameter holding the API key (Lambda). |
| `GEMINI_API_KEY` | API key for local development; takes precedence over SSM. |
| `GEMINI_MODEL` | Optional. Defaults to `gemini-3.5-flash-lite`. |
| `SPEECH_MAX_CHARS` | Optional. Maximum spoken answer length, default 600. |
| `CONTEXT_TURNS` | Optional. Previous question/answer pairs sent to the model within one Alexa session (default 4, `0` turns the context off). The default lives in `skill/context.py`. |
| `ALLOW_NO_SKILL_ID=1` | Local runs only: skips the skill ID check. |

The API key is never logged or printed. Do not paste it in commands or chats; enter it with `read -s GEMINI_API_KEY; export GEMINI_API_KEY`.

## Development

Requires Python 3.10+ (CI uses 3.14).

```bash
python3 scripts/lock.py        # after changing a pin: rewrites requirements*.txt with sha256 hashes (stdlib only, needs network)
./scripts/init.sh              # venv, dependencies, tests, dependency audit, mocked smoke test
./scripts/verify.sh            # the verification command CI runs: unittest + pip-audit
./scripts/smoke.sh --real      # also calls the real Gemini API (needs GEMINI_API_KEY)
```

## Status

Implemented and tested locally: interaction models, intent handlers, Gemini client, SSM key loading, speech cleanup, error handling, follow-up questions, CI.

Not done yet: deployment to AWS Lambda, certification and testing on a real Echo device, and the privacy policy contact details. `boto3` is provided by the Lambda runtime and is not in `requirements.txt`; the SSM path needs it installed to run locally.
