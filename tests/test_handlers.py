import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skill.lambda_function import MESSAGES, lambda_handler  # noqa: E402


def event(request, locale="es-US"):
    request = {"requestId": "amzn1.echo-api.request.test", "timestamp": "2026-01-01T00:00:00Z",
               "locale": locale, **request}
    return {
        "version": "1.0",
        "session": {"new": True, "sessionId": "amzn1.echo-api.session.test",
                    "application": {"applicationId": "amzn1.ask.skill.test"},
                    "user": {"userId": "amzn1.ask.account.test"}},
        "context": {"System": {"application": {"applicationId": "amzn1.ask.skill.test"},
                               "user": {"userId": "amzn1.ask.account.test"}}},
        "request": request,
    }


def intent(name, locale="es-US"):
    return event({"type": "IntentRequest", "intent": {"name": name, "confirmationStatus": "NONE"}}, locale)


def speech(resp):
    return resp["response"]["outputSpeech"]["ssml"]


class HandlerTest(unittest.TestCase):
    def test_launch_greets_and_reprompts_per_locale(self):
        for locale, lang in (("es-US", "es"), ("es-ES", "es"), ("en-US", "en")):
            with self.subTest(locale=locale):
                resp = lambda_handler(event({"type": "LaunchRequest"}, locale), None)
                self.assertIn(MESSAGES[lang]["welcome"], speech(resp))
                self.assertIn(MESSAGES[lang]["welcome_reprompt"], resp["response"]["reprompt"]["outputSpeech"]["ssml"])
                self.assertFalse(resp["response"]["shouldEndSession"])

    def test_help_and_fallback_keep_session_open(self):
        for name, key in (("AMAZON.HelpIntent", "help"), ("AMAZON.FallbackIntent", "fallback")):
            for locale, lang in (("es-ES", "es"), ("en-US", "en")):
                with self.subTest(intent=name, locale=locale):
                    resp = lambda_handler(intent(name, locale), None)
                    self.assertIn(MESSAGES[lang][key], speech(resp))
                    self.assertIn("reprompt", resp["response"])
                    self.assertFalse(resp["response"]["shouldEndSession"])

    def test_stop_and_cancel_end_session(self):
        for name in ("AMAZON.StopIntent", "AMAZON.CancelIntent"):
            with self.subTest(intent=name):
                resp = lambda_handler(intent(name, "en-US"), None)
                self.assertIn(MESSAGES["en"]["bye"], speech(resp))
                self.assertTrue(resp["response"]["shouldEndSession"])

    def test_session_ended_has_no_speech(self):
        resp = lambda_handler(event({"type": "SessionEndedRequest", "reason": "USER_INITIATED"}), None)
        self.assertNotIn("outputSpeech", resp["response"])

    def test_unknown_locale_falls_back_to_english(self):
        resp = lambda_handler(event({"type": "LaunchRequest"}, "fr-FR"), None)
        self.assertIn(MESSAGES["en"]["welcome"], speech(resp))


if __name__ == "__main__":
    unittest.main()
