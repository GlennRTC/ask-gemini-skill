import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skill.gemini import ask_gemini  # noqa: E402
from skill.guardrails import DISCLAIMERS, HEALTH_PROMPTS, classify, emergency_message  # noqa: E402
from test_handlers import event, intent, lambda_handler, speech  # noqa: E402


def ask(query, locale):
    slots = {"query": {"name": "query", "value": query, "confirmationStatus": "NONE"}}
    return intent("AskGeminiIntent", locale, slots)


class ClassifyTest(unittest.TestCase):
    def test_health_questions(self):
        cases = [
            ("es-US", "es la dosis ideal de acetaminofén para un adulto de treinta y cinco años"),
            ("es-ES", "cuántos miligramos de ibuprofeno puedo tomar"),
            ("es-US", "qué síntomas tiene la diabetes"),
            ("en-US", "what is the right dose of acetaminophen for an adult"),
            ("en-US", "can I take aspirin if I am pregnant"),
        ]
        for locale, query in cases:
            with self.subTest(query=query):
                self.assertEqual(classify(query, locale), "health")

    def test_emergency_questions(self):
        cases = [("es-US", "me quiero morir"), ("es-ES", "qué pasa en una sobredosis"),
                 ("en-US", "I want to die"), ("en-US", "how much would be an overdose")]
        for locale, query in cases:
            with self.subTest(query=query):
                self.assertEqual(classify(query, locale), "emergency")

    def test_ordinary_questions_are_not_flagged(self):
        for locale, query in (("es-US", "cuál es la capital de Francia"), ("en-US", "who wrote Don Quixote"),
                              ("en-US", "why is the sky blue")):
            with self.subTest(query=query):
                self.assertIsNone(classify(query, locale))

    def test_words_not_substrings(self):
        self.assertIsNone(classify("what is a kilogram", "en-US"))  # "mg" is not inside "kilogram"


class HandlerGuardrailTest(unittest.TestCase):
    def test_emergency_skips_gemini_and_ends_session(self):
        for locale in ("es-US", "es-ES", "en-US"):
            with self.subTest(locale=locale):
                with mock.patch("skill.lambda_function.ask_gemini") as fake:
                    resp = lambda_handler(ask("me quiero morir" if locale != "en-US" else "I want to die", locale), None)
                fake.assert_not_called()
                self.assertIn(emergency_message(locale), speech(resp))
                self.assertTrue(resp["response"]["shouldEndSession"])

    def test_health_adds_prompt_and_disclaimer(self):
        for locale, lang in (("es-US", "es"), ("en-US", "en")):
            with self.subTest(locale=locale):
                query = "dosis de paracetamol" if lang == "es" else "paracetamol dose"
                with mock.patch("skill.lambda_function.ask_gemini", return_value="Consulta a tu médico.") as fake:
                    resp = lambda_handler(ask(query, locale), None)
                fake.assert_called_once_with(query, locale, extra_instruction=HEALTH_PROMPTS[lang])
                self.assertIn(DISCLAIMERS[lang], speech(resp))
                self.assertFalse(resp["response"]["shouldEndSession"])

    def test_ordinary_question_has_no_disclaimer(self):
        with mock.patch("skill.lambda_function.ask_gemini", return_value="Paris.") as fake:
            resp = lambda_handler(ask("capital of France", "en-US"), None)
        fake.assert_called_once_with("capital of France", "en-US")
        self.assertNotIn(DISCLAIMERS["en"], speech(resp))

    def test_extra_instruction_reaches_system_prompt(self):
        calls = {}

        def generate_content(**kwargs):
            calls.update(kwargs)
            return mock.Mock(text="ok", prompt_feedback=None)

        client = mock.Mock(models=mock.Mock(generate_content=generate_content))
        ask_gemini("x", "en-US", client=client, extra_instruction="EXTRA-RULE")
        self.assertIn("EXTRA-RULE", calls["config"].system_instruction)


if __name__ == "__main__":
    unittest.main()
