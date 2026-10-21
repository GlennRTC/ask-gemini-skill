"""Local end-to-end smoke test: Alexa request JSON -> lambda_handler -> spoken response.

Default: Gemini is mocked. With --real (and GEMINI_API_KEY or GEMINI_API_KEY_PARAM set)
the AskGeminiIntent request also goes to the real Gemini API.
"""
import os
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skill.lambda_function import MESSAGES, lambda_handler  # noqa: E402

ERROR_TEXTS = {v for lang in MESSAGES.values() for k, v in lang.items() if k.startswith("error")}

LOCALE = "en-US"
QUERY = "what is the capital of France"


def event(request):
    app = {"applicationId": "amzn1.ask.skill.smoke"}
    user = {"userId": "amzn1.ask.account.smoke"}
    return {
        "version": "1.0",
        "session": {"new": True, "sessionId": "amzn1.echo-api.session.smoke", "application": app, "user": user},
        "context": {"System": {"application": app, "user": user}},
        "request": {"requestId": "amzn1.echo-api.request.smoke", "timestamp": "2026-01-01T00:00:00Z",
                    "locale": LOCALE, **request},
    }


LAUNCH = event({"type": "LaunchRequest"})
ASK = event({"type": "IntentRequest", "intent": {
    "name": "AskGeminiIntent", "confirmationStatus": "NONE",
    "slots": {"query": {"name": "query", "value": QUERY, "confirmationStatus": "NONE"}}}})


def speech(resp):
    return resp["response"]["outputSpeech"]["ssml"]


def check(label, resp):
    ssml = speech(resp)
    assert ssml.startswith("<speak>") and len(ssml) > len("<speak></speak>"), f"{label}: empty speech"
    # The handler turns Gemini/SSM failures into a spoken error, which is still valid SSML.
    assert not any(text in ssml for text in ERROR_TEXTS), f"{label}: handler answered with an error message"
    print(f"ok  {label}: {ssml}")


def main():
    real = "--real" in sys.argv
    if real and not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY_PARAM")):
        sys.exit("--real needs GEMINI_API_KEY or GEMINI_API_KEY_PARAM (value is never printed)")

    check("launch", lambda_handler(LAUNCH, None))
    with mock.patch("skill.lambda_function.ask_gemini", return_value="Paris is the capital of France."):
        check("ask (mocked Gemini)", lambda_handler(ASK, None))
    if real:
        check("ask (real Gemini)", lambda_handler(ASK, None))
    else:
        print("skip real Gemini call (pass --real to enable)")


if __name__ == "__main__":
    main()
