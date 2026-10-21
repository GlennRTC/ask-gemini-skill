import json
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402
from ask_sdk_core.serialize import DefaultSerializer  # noqa: E402
from ask_sdk_model import RequestEnvelope  # noqa: E402

from skill import location  # noqa: E402
from test_handlers import intent, lambda_handler, speech  # noqa: E402

SYSTEM = {
    "device": {"deviceId": "amzn1.ask.device.test", "supportedInterfaces": {}},
    "apiEndpoint": "https://api.amazonalexa.com",
    "apiAccessToken": "synthetic-token",
}


def ask(query, locale="es-US", consent=True, **system_overrides):
    slots = {"query": {"name": "query", "value": query, "confirmationStatus": "NONE"}}
    req = intent("AskGeminiIntent", locale, slots)
    req["context"]["System"].update({**SYSTEM, **system_overrides})
    if consent:
        req["context"]["System"]["user"]["permissions"] = {"consentToken": "synthetic-consent"}
    return req


def envelope(req):
    return DefaultSerializer().deserialize(json.dumps(req), RequestEnvelope)


def http(status, body=None):
    resp = mock.Mock(status_code=status)
    resp.json.return_value = body or {}
    return resp


def miami():
    return http(200, {"countryCode": "US", "postalCode": "33101"})


class PlaceQuestionTest(unittest.TestCase):
    def test_proximity_questions(self):
        for locale, q in (("es-US", "restaurantes cerca de mí"), ("es-US", "qué hay para hacer en mi ciudad"),
                          ("es-ES", "parques por aquí"), ("en-US", "coffee shops nearby"),
                          ("en-US", "things to do in my area")):
            with self.subTest(q=q):
                self.assertTrue(location.is_place_question(q, locale))

    def test_generic_questions_do_not_use_location(self):
        for locale, q in (("es-US", "dónde murió Cervantes"), ("en-US", "where is the Eiffel Tower"),
                          ("en-US", "what is the local time in Tokyo"), ("en-US", "how did humans get here"),
                          ("es-US", "quién escribió Don Quijote")):
            with self.subTest(q=q):
                self.assertFalse(location.is_place_question(q, locale))


class PostalCodeTest(unittest.TestCase):
    def test_reads_the_postal_code_safely(self):
        with mock.patch("skill.location.requests.get", return_value=miami()) as get:
            result = location.postal_code(envelope(ask("x")))
        self.assertEqual(result, ("ok", "US", "33101"))
        self.assertEqual(get.call_args.args[0], "https://api.amazonalexa.com/v1/devices/amzn1.ask.device.test"
                                                "/settings/address/countryAndPostalCode")
        self.assertEqual(get.call_args.kwargs["headers"]["Authorization"], "Bearer synthetic-token")
        self.assertFalse(get.call_args.kwargs["allow_redirects"])

    def test_status_and_format_mapping(self):
        cases = [
            (http(403), ("denied", None, None)),
            (http(204), ("none", None, None)),
            (http(500), ("none", None, None)),
            (http(200, {"countryCode": "US", "postalCode": "98109"}), ("none", None, None)),
            (http(200, {"countryCode": "US", "postalCode": "IGNORE ALL"}), ("none", None, None)),
            (http(200, {"countryCode": "FR", "postalCode": "75001"}), ("none", None, None)),
            (http(200, {"countryCode": "ES", "postalCode": "28013"}), ("ok", "ES", "28013")),
            (http(200, {"countryCode": "US", "postalCode": "33101-1234"}), ("ok", "US", "33101-1234")),
        ]
        for resp, expected in cases:
            with self.subTest(expected=expected, body=resp.json.return_value):
                with mock.patch("skill.location.requests.get", return_value=resp):
                    self.assertEqual(location.postal_code(envelope(ask("x"))), expected)

    def test_no_consent_skips_the_api(self):
        with mock.patch("skill.location.requests.get") as get:
            self.assertEqual(location.postal_code(envelope(ask("x", consent=False))), ("denied", None, None))
        get.assert_not_called()

    def test_token_only_goes_to_amazon_hosts(self):
        for endpoint in ("https://evil.example.com", "http://api.amazonalexa.com", "http://169.254.169.254",
                         "https://api.amazonalexa.com.evil.com", "https://api.amazonalexa.com:8443",
                         "https://api.amazonalexa.com/proxy"):
            with self.subTest(endpoint=endpoint):
                with mock.patch("skill.location.requests.get") as get:
                    result = location.postal_code(envelope(ask("x", apiEndpoint=endpoint)))
                get.assert_not_called()
                self.assertEqual(result, ("none", None, None))

    def test_device_id_is_escaped(self):
        device = {"deviceId": "../../other?x=1", "supportedInterfaces": {}}
        with mock.patch("skill.location.requests.get", return_value=miami()) as get:
            location.postal_code(envelope(ask("x", device=device)))
        self.assertIn("/v1/devices/..%2F..%2Fother%3Fx%3D1/settings", get.call_args.args[0])

    def test_errors_and_slow_api_degrade_within_the_deadline(self):
        with mock.patch("skill.location.requests.get", side_effect=requests.Timeout()):
            self.assertEqual(location.postal_code(envelope(ask("x"))), ("none", None, None))

        def slow(*args, **kwargs):
            time.sleep(0.5)
            return miami()

        with mock.patch("skill.location.DEADLINE_S", 0.05), mock.patch("skill.location.requests.get", side_effect=slow):
            started = time.monotonic()
            self.assertEqual(location.postal_code(envelope(ask("x"))), ("none", None, None))
            self.assertLess(time.monotonic() - started, 0.3)


class HandlerLocationTest(unittest.TestCase):
    def test_place_question_sends_postal_code_and_a_time_budget(self):
        with mock.patch("skill.location.requests.get", return_value=miami()), \
                mock.patch("skill.lambda_function.ask_gemini", return_value="Prueba el parque Bayfront.") as fake:
            resp = lambda_handler(ask("parques cerca de mí"), None)
        self.assertIn("33101", fake.call_args.kwargs["extra_instruction"])
        self.assertLessEqual(fake.call_args.kwargs["timeout_s"], 4.5)
        self.assertIn("Bayfront", speech(resp))

    def test_without_consent_answers_and_sends_a_card(self):
        with mock.patch("skill.location.requests.get") as get, \
                mock.patch("skill.lambda_function.ask_gemini", return_value="Depende de tu zona.") as fake:
            resp = lambda_handler(ask("restaurantes cerca de mí", consent=False), None)
        get.assert_not_called()
        fake.assert_called_once()
        self.assertNotIn("extra_instruction", fake.call_args.kwargs)
        self.assertIn("Depende de tu zona.", speech(resp))
        self.assertIn(location.permission_note("es-US"), speech(resp))
        self.assertEqual(resp["response"]["card"]["type"], "AskForPermissionsConsent")
        self.assertEqual(resp["response"]["card"]["permissions"], [location.PERMISSION])
        self.assertFalse(resp["response"]["shouldEndSession"])

    def test_non_place_question_never_calls_the_address_api(self):
        with mock.patch("skill.location.requests.get") as get, \
                mock.patch("skill.lambda_function.ask_gemini", return_value="Cervantes.") as fake:
            lambda_handler(ask("quién escribió Don Quijote"), None)
        get.assert_not_called()
        self.assertNotIn("timeout_s", fake.call_args.kwargs)

    def test_postal_code_repeated_by_the_model_is_scrubbed_from_history_and_logs(self):
        with mock.patch("skill.location.requests.get", return_value=miami()), \
                mock.patch("skill.lambda_function.ask_gemini", return_value="En el 33101 prueba Bayfront."):
            with self.assertLogs("skill.lambda_function", level="INFO") as logs:
                resp = lambda_handler(ask("parques cerca de mí"), None)
        self.assertNotIn("33101", "\n".join(logs.output))
        self.assertNotIn("33101", json.dumps(resp.get("sessionAttributes")))


if __name__ == "__main__":
    unittest.main()
