import json
import unittest
from pathlib import Path

INFRA = Path(__file__).resolve().parent.parent / "infra"


class RolePolicyTest(unittest.TestCase):
    def statements(self):
        text = (INFRA / "role-policy.json").read_text(encoding="utf-8")
        for name, value in (("__REGION__", "us-east-1"), ("__ACCOUNT_ID__", "123456789012"),
                            ("__KEY_PARAM__", "/ask-gemini/api-key"), ("__FUNCTION_NAME__", "fn")):
            text = text.replace(name, value)
        return {s["Sid"]: s for s in json.loads(text)["Statement"]}

    def test_key_access_is_one_exact_parameter(self):
        stmt = self.statements()["ReadGeminiKey"]
        self.assertEqual(stmt["Action"], "ssm:GetParameter")
        self.assertEqual(stmt["Resource"], "arn:aws:ssm:us-east-1:123456789012:parameter/ask-gemini/api-key")

    def test_no_statement_grants_wildcard_actions(self):
        for stmt in self.statements().values():
            actions = stmt["Action"] if isinstance(stmt["Action"], list) else [stmt["Action"]]
            self.assertFalse(any("*" in a for a in actions), stmt["Sid"])

    def test_decrypt_is_limited_to_ssm(self):
        stmt = self.statements()["DecryptKeyViaSsm"]
        self.assertEqual(stmt["Condition"]["StringEquals"]["kms:ViaService"], "ssm.us-east-1.amazonaws.com")

    def test_logs_limited_to_own_group(self):
        stmt = self.statements()["WriteOwnLogs"]
        self.assertIn("/aws/lambda/fn:", stmt["Resource"])
        self.assertNotIn("logs:CreateLogGroup", stmt["Action"])

    def test_trust_policy_is_lambda_only(self):
        trust = json.loads((INFRA / "trust-policy.json").read_text(encoding="utf-8"))
        self.assertEqual(trust["Statement"][0]["Principal"], {"Service": "lambda.amazonaws.com"})


if __name__ == "__main__":
    unittest.main()
