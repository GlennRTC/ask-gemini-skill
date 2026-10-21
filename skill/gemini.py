import os

import httpx
from google import genai
from google.genai import errors, types

DEFAULT_MODEL = "gemini-3.5-flash-lite"  # override with GEMINI_MODEL; older 2.5 models 404 for new users
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


def ask_gemini(query, locale, api_key=None, client=None, timeout_s=DEFAULT_TIMEOUT_S, extra_instruction=None):
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
    try:
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL), contents=query[:MAX_QUERY_CHARS], config=config
        )
    except (httpx.TimeoutException, TimeoutError):
        raise GeminiError("timeout") from None
    except errors.ClientError as exc:
        raise GeminiError("quota" if exc.code == 429 else "api", exc.code) from None
    except errors.APIError as exc:
        raise GeminiError("api", getattr(exc, "code", None)) from None

    feedback = getattr(response, "prompt_feedback", None)
    if feedback is not None and getattr(feedback, "block_reason", None):
        raise GeminiError("blocked")
    text = (response.text or "").strip()
    if not text:
        raise GeminiError("blocked")
    return text
