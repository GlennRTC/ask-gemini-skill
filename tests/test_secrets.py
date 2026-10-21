import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skill import secrets  # noqa: E402

FAKE_VALUE = "synthetic-test-value"


class FakeSsm:
    def __init__(self, exc=None):
        self.calls = []
        self.exc = exc

    def get_parameter(self, **kwargs):
        self.calls.append(kwargs)
        if self.exc:
            raise self.exc
        return {"Parameter": {"Value": FAKE_VALUE}}


class SecretsTest(unittest.TestCase):
    def setUp(self):
        secrets.clear_cache()
        self.addCleanup(secrets.clear_cache)

    def env(self, **values):
        patcher = mock.patch.dict(os.environ, values, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_env_var_wins(self):
        self.env(GEMINI_API_KEY=FAKE_VALUE)
        self.assertEqual(secrets.get_gemini_api_key(FakeSsm()), FAKE_VALUE)

    def test_ssm_decrypts_and_caches(self):
        self.env(GEMINI_API_KEY_PARAM="/ask-gemini/api-key")
        ssm = FakeSsm()
        self.assertEqual(secrets.get_gemini_api_key(ssm), FAKE_VALUE)
        self.assertEqual(secrets.get_gemini_api_key(ssm), FAKE_VALUE)
        self.assertEqual(ssm.calls, [{"Name": "/ask-gemini/api-key", "WithDecryption": True}])

    def test_missing_config_raises(self):
        self.env()
        with self.assertRaises(secrets.SecretError):
            secrets.get_gemini_api_key(FakeSsm())

    def test_ssm_failure_hides_details(self):
        self.env(GEMINI_API_KEY_PARAM="/p")
        with self.assertRaises(secrets.SecretError) as ctx:
            secrets.get_gemini_api_key(FakeSsm(exc=RuntimeError(f"boom {FAKE_VALUE}")))
        self.assertNotIn(FAKE_VALUE, str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
