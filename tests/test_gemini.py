import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402
from google.genai import errors  # noqa: E402

from skill.gemini import GeminiError, ask_gemini  # noqa: E402


def fake_client(result=None, exc=None):
    def generate_content(**kwargs):
        generate_content.kwargs = kwargs
        if exc:
            raise exc
        return result

    return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)), generate_content


def response(text, block_reason=None):
    return SimpleNamespace(text=text, prompt_feedback=SimpleNamespace(block_reason=block_reason))


class AskGeminiTest(unittest.TestCase):
    def test_returns_text_and_sends_query(self):
        client, call = fake_client(response(" Paris. "))
        self.assertEqual(ask_gemini("capital of France", "en-US", client=client), "Paris.")
        self.assertEqual(call.kwargs["contents"], "capital of France")

    def test_caps_query_and_output(self):
        client, call = fake_client(response("ok"))
        ask_gemini("a" * 5000, "en-US", client=client)
        self.assertEqual(len(call.kwargs["contents"]), 500)
        self.assertEqual(call.kwargs["config"].max_output_tokens, 300)

    def test_prompt_follows_locale_language(self):
        for locale, word in (("es-ES", "español"), ("es-US", "español"), ("en-US", "English"), ("fr-FR", "English")):
            with self.subTest(locale=locale):
                client, call = fake_client(response("ok"))
                ask_gemini("x", locale, client=client)
                self.assertIn(word, call.kwargs["config"].system_instruction)

    def test_timeout_maps_to_error(self):
        client, _ = fake_client(exc=httpx.ReadTimeout("slow"))
        with self.assertRaises(GeminiError) as ctx:
            ask_gemini("x", "en-US", client=client)
        self.assertEqual(ctx.exception.kind, "timeout")

    def test_quota_and_api_errors(self):
        for code, kind in ((429, "quota"), (400, "api")):
            with self.subTest(code=code):
                client, _ = fake_client(exc=errors.ClientError(code, {"error": {"message": "m"}}))
                with self.assertRaises(GeminiError) as ctx:
                    ask_gemini("x", "en-US", client=client)
                self.assertEqual(ctx.exception.kind, kind)

    def test_server_error_maps_to_api(self):
        client, _ = fake_client(exc=errors.ServerError(500, {"error": {"message": "m"}}))
        with self.assertRaises(GeminiError) as ctx:
            ask_gemini("x", "en-US", client=client)
        self.assertEqual(ctx.exception.kind, "api")

    def test_blocked_prompt_or_empty_text(self):
        for resp in (response(None, block_reason="SAFETY"), response("")):
            with self.subTest(resp=resp):
                client, _ = fake_client(resp)
                with self.assertRaises(GeminiError) as ctx:
                    ask_gemini("x", "en-US", client=client)
                self.assertEqual(ctx.exception.kind, "blocked")


if __name__ == "__main__":
    unittest.main()
