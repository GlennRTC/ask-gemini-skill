import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skill.voice import VOICES, with_voice  # noqa: E402
from test_handlers import MESSAGES, event, intent, lambda_handler  # noqa: E402


def ssml(resp, reprompt=False):
    if reprompt:
        return resp["response"]["reprompt"]["outputSpeech"]["ssml"]
    return resp["response"]["outputSpeech"]["ssml"]


class VoiceTest(unittest.TestCase):
    def test_each_locale_speaks_with_its_voice(self):
        for locale, lang in (("es-US", "es"), ("es-ES", "es"), ("en-US", "en")):
            with self.subTest(locale=locale):
                resp = lambda_handler(event({"type": "LaunchRequest"}, locale), None)
                expected = f'<speak><voice name="{VOICES[locale]}">{MESSAGES[lang]["welcome"]}</voice></speak>'
                self.assertEqual(ssml(resp), expected)
                self.assertTrue(ssml(resp, reprompt=True).startswith(f'<speak><voice name="{VOICES[locale]}">'))

    def test_es_us_uses_miguel(self):
        self.assertEqual(VOICES["es-US"], "Miguel")

    def test_answers_and_errors_use_the_voice(self):
        slots = {"query": {"name": "query", "value": "x", "confirmationStatus": "NONE"}}
        with mock.patch("skill.lambda_function.ask_gemini", return_value="Hola."):
            resp = lambda_handler(intent("AskGeminiIntent", "es-US", slots), None)
        self.assertIn('<voice name="Miguel">Hola.', ssml(resp))
        with mock.patch("skill.lambda_function.ask_gemini", side_effect=RuntimeError("boom")):
            resp = lambda_handler(intent("AskGeminiIntent", "es-US", slots), None)
        self.assertIn('<voice name="Miguel">', ssml(resp))

    def test_unknown_locale_and_empty_voice_keep_alexa(self):
        resp = lambda_handler(event({"type": "LaunchRequest"}, "fr-FR"), None)
        self.assertNotIn("<voice", ssml(resp))
        self.assertEqual(with_voice("<speak>hi</speak>", ""), "<speak>hi</speak>")

    def test_session_end_without_speech_is_untouched(self):
        resp = lambda_handler(event({"type": "SessionEndedRequest", "reason": "USER_INITIATED"}), None)
        self.assertNotIn("outputSpeech", resp["response"])


if __name__ == "__main__":
    unittest.main()
