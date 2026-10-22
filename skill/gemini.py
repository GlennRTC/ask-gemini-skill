import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
from google import genai
from google.genai import errors, types

DEFAULT_MODEL = "gemini-3.5-flash-lite"  # override with GEMINI_MODEL; older 2.5 models 404 for new users
# Tried when the main model is overloaded (503), slow, rate-limited or missing; "" turns the fallback off.
DEFAULT_FALLBACK_MODEL = "gemini-3.8-flash"
# Share of the time budget the main model may use before the fallback gets its turn.
PRIMARY_SHARE = 0.55
MIN_ATTEMPT_S = 0.5
_FALLBACK_STATUSES = {None, 404, 429, 500, 503, 504}
# Alexa cuts the request at about 8 s; a cold start can take ~2 s before this call, so give up at 4.5 s.
DEFAULT_TIMEOUT_S = 4.5
MAX_ANSWER_WORDS = 60
MAX_QUERY_CHARS = 500
MAX_OUTPUT_TOKENS = 300  # hard cap; the prompt's word limit alone can be ignored

SAFETY_SETTINGS = [
    types.SafetySetting(category=category, threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE)
    for category in (
        types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    )
]

SYSTEM_PROMPTS = {
    "es": f"Eres un asistente de voz. Responde siempre en español, de forma clara y breve "
          f"(máximo {MAX_ANSWER_WORDS} palabras), sin markdown, listas ni enlaces.",
    "en": f"You are a voice assistant. Always answer in English, clearly and briefly "
          f"(at most {MAX_ANSWER_WORDS} words), with no markdown, lists or links.",
}


logger = logging.getLogger(__name__)


class GeminiError(Exception):
    """kind is one of: timeout, quota, blocked, api."""

    def __init__(self, kind, status=None):
        super().__init__(kind)
        self.kind = kind
        self.status = status  # HTTP status from the API when known; safe to log


_client = None


def _get_client(api_key, timeout_s):
    global _client
    if _client is None:
        # HttpOptions.timeout would send X-Server-Timeout, which the API rejects below 10 s
        # (400), so the limit is enforced client-side through httpx.
        _client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(client_args={"timeout": timeout_s})
        )
    return _client


def _contents(query, history):
    current = query[:MAX_QUERY_CHARS]
    if not history:
        return current
    turns = []
    for turn in history:
        turns.append(types.Content(role="user", parts=[types.Part(text=turn["q"][:MAX_QUERY_CHARS])]))
        turns.append(types.Content(role="model", parts=[types.Part(text=turn["a"])]))
    turns.append(types.Content(role="user", parts=[types.Part(text=current)]))
    return turns


def ask_gemini(query, locale, api_key=None, client=None, timeout_s=DEFAULT_TIMEOUT_S, extra_instruction=None,
               history=None):
    if client is None:
        if api_key is None:
            from .secrets import get_gemini_api_key

            api_key = get_gemini_api_key()
        client = _get_client(api_key, timeout_s)

    lang = locale.split("-")[0].lower() if locale else "en"
    instruction = SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS["en"])
    if extra_instruction:
        instruction = f"{instruction} {extra_instruction}"
    config = types.GenerateContentConfig(
        system_instruction=instruction, max_output_tokens=MAX_OUTPUT_TOKENS,
        safety_settings=SAFETY_SETTINGS,
    )
    contents = _contents(query, history)
    models = [os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)]
    fallback = os.environ.get("GEMINI_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL)
    if fallback and fallback != models[0]:
        models.append(fallback)

    started = time.monotonic()
    last_error = None
    for index, model in enumerate(models):
        remaining = timeout_s - (time.monotonic() - started)
        budget = remaining * PRIMARY_SHARE if index < len(models) - 1 else remaining
        if index > 0 and budget < MIN_ATTEMPT_S:
            break
        try:
            return _generate(client, model, contents, config, budget)
        except GeminiError as exc:
            last_error = exc
            if exc.kind in ("blocked",) or (exc.kind == "api" and exc.status not in _FALLBACK_STATUSES):
                raise
            logger.warning("gemini_attempt_failed model_index=%d kind=%s status=%s", index, exc.kind, exc.status)
    raise last_error or GeminiError("timeout")


def _generate(client, model, contents, config, budget_s):
    # httpx timeouts apply per phase, not to the whole call, and a stalled call once ran into the
    # Lambda limit; so the call also gets a hard wall-clock deadline in a worker thread.
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(client.models.generate_content, model=model, contents=contents, config=config)
        response = future.result(timeout=budget_s)
    except (httpx.TimeoutException, TimeoutError):
        raise GeminiError("timeout") from None
    except errors.ClientError as exc:
        raise GeminiError("quota" if exc.code == 429 else "api", exc.code) from None
    except errors.APIError as exc:
        raise GeminiError("api", getattr(exc, "code", None)) from None
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    feedback = getattr(response, "prompt_feedback", None)
    if feedback is not None and getattr(feedback, "block_reason", None):
        raise GeminiError("blocked")
    text = (response.text or "").strip()
    if not text:
        raise GeminiError("blocked")
    return text
