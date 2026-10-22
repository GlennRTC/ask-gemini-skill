import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402
from google.genai import errors  # noqa: E402

from skill import gemini  # noqa: E402
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

    def test_client_timeout_is_client_side_only(self):
        # A server-side deadline under 10 s is rejected by the API with HTTP 400.
        gemini._client = None
        self.addCleanup(setattr, gemini, "_client", None)
        with mock.patch.object(gemini.genai, "Client") as client_cls:
            gemini._get_client("synthetic", 6.0)
        options = client_cls.call_args.kwargs["http_options"]
        self.assertIsNone(options.timeout)
        self.assertEqual(options.client_args, {"timeout": 6.0})

    def test_safety_settings_are_sent(self):
        client, call = fake_client(response("ok"))
        ask_gemini("x", "en-US", client=client)
        settings = call.kwargs["config"].safety_settings
        self.assertEqual(len(settings), 4)
        self.assertTrue(all(s.threshold.name == "BLOCK_MEDIUM_AND_ABOVE" for s in settings))

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

    def test_stalled_call_hits_the_hard_deadline(self):
        import time

        def stalled(**kwargs):
            time.sleep(0.5)
            return response("late")

        client = SimpleNamespace(models=SimpleNamespace(generate_content=stalled))
        started = time.monotonic()
        with self.assertRaises(GeminiError) as ctx:
            ask_gemini("x", "en-US", client=client, timeout_s=0.05)
        self.assertEqual(ctx.exception.kind, "timeout")
        self.assertLess(time.monotonic() - started, 0.3)

    def test_falls_back_to_the_second_model_on_503(self):
        calls = []

        def generate_content(**kwargs):
            calls.append(kwargs["model"])
            if len(calls) == 1:
                raise errors.ServerError(503, {"error": {"message": "overloaded"}})
            return response("from fallback")

        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        with mock.patch.dict("os.environ", {"GEMINI_MODEL": "main-model", "GEMINI_FALLBACK_MODEL": "backup-model"}):
            self.assertEqual(ask_gemini("x", "en-US", client=client), "from fallback")
        self.assertEqual(calls, ["main-model", "backup-model"])

    def test_slow_main_model_leaves_time_for_the_fallback(self):
        import time

        def generate_content(**kwargs):
            if kwargs["model"] == "main-model":
                time.sleep(2.0)
            return response("from " + kwargs["model"])

        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        with mock.patch.dict("os.environ", {"GEMINI_MODEL": "main-model", "GEMINI_FALLBACK_MODEL": "backup-model"}):
            started = time.monotonic()
            self.assertEqual(ask_gemini("x", "en-US", client=client, timeout_s=2.0), "from backup-model")
        self.assertLess(time.monotonic() - started, 2.0)

    def test_no_fallback_for_blocked_bad_requests_or_when_disabled(self):
        calls = []

        def blocked(**kwargs):
            calls.append(kwargs["model"])
            return response(None, block_reason="SAFETY")

        def bad_request(**kwargs):
            calls.append(kwargs["model"])
            raise errors.ClientError(400, {"error": {"message": "bad"}})

        env = {"GEMINI_MODEL": "main-model", "GEMINI_FALLBACK_MODEL": "backup-model"}
        for fn in (blocked, bad_request):
            calls.clear()
            client = SimpleNamespace(models=SimpleNamespace(generate_content=fn))
            with mock.patch.dict("os.environ", env), self.assertRaises(GeminiError):
                ask_gemini("x", "en-US", client=client)
            self.assertEqual(calls, ["main-model"])
        calls.clear()
        client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **k: (_ for _ in ()).throw(
            errors.ServerError(503, {"error": {"message": "m"}}))))
        with mock.patch.dict("os.environ", {**env, "GEMINI_FALLBACK_MODEL": ""}), self.assertRaises(GeminiError) as ctx:
            ask_gemini("x", "en-US", client=client)
        self.assertEqual(ctx.exception.status, 503)

    def test_both_models_failing_raises_the_last_error(self):
        client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **k: (_ for _ in ()).throw(
            errors.ServerError(503, {"error": {"message": "m"}}))))
        with self.assertRaises(GeminiError) as ctx:
            ask_gemini("x", "en-US", client=client)
        self.assertEqual((ctx.exception.kind, ctx.exception.status), ("api", 503))

    def test_quota_and_api_errors(self):
        for code, kind in ((429, "quota"), (400, "api")):
            with self.subTest(code=code):
                client, _ = fake_client(exc=errors.ClientError(code, {"error": {"message": "m"}}))
                with self.assertRaises(GeminiError) as ctx:
                    ask_gemini("x", "en-US", client=client)
                self.assertEqual(ctx.exception.kind, kind)
                self.assertEqual(ctx.exception.status, code)

    def test_server_error_maps_to_api(self):
        client, _ = fake_client(exc=errors.ServerError(500, {"error": {"message": "m"}}))
        with self.assertRaises(GeminiError) as ctx:
            ask_gemini("x", "en-US", client=client)
        self.assertEqual(ctx.exception.kind, "api")

    def test_blocked_prompt_or_empty_text(self):
        # text is None when a candidate is blocked by safety filters (finish_reason SAFETY).
        for resp in (response(None, block_reason="SAFETY"), response(""), response(None)):
            with self.subTest(resp=resp):
                client, _ = fake_client(resp)
                with self.assertRaises(GeminiError) as ctx:
                    ask_gemini("x", "en-US", client=client)
                self.assertEqual(ctx.exception.kind, "blocked")


if __name__ == "__main__":
    unittest.main()
