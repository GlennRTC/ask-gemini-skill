import json
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "skill-package"
LOCALES = ["es-US", "es-ES", "en-US"]
BUILTINS = {"AMAZON.HelpIntent", "AMAZON.StopIntent", "AMAZON.CancelIntent", "AMAZON.FallbackIntent", "AMAZON.YesIntent", "AMAZON.NoIntent"}


class InteractionModelTest(unittest.TestCase):
    def model(self, locale):
        path = PKG / "interactionModels" / "custom" / f"{locale}.json"
        return json.loads(path.read_text(encoding="utf-8"))["interactionModel"]["languageModel"]

    def test_manifest_declares_all_locales(self):
        manifest = json.loads((PKG / "skill.json").read_text(encoding="utf-8"))["manifest"]
        self.assertEqual(sorted(manifest["publishingInformation"]["locales"]), sorted(LOCALES))

    def test_each_locale_has_ask_intent_with_search_query_slot(self):
        for locale in LOCALES:
            with self.subTest(locale=locale):
                lm = self.model(locale)
                intent = next(i for i in lm["intents"] if i["name"] == "AskGeminiIntent")
                self.assertEqual(intent["slots"], [{"name": "query", "type": "AMAZON.SearchQuery"}])
                self.assertGreaterEqual(len(intent["samples"]), 5)
                for sample in intent["samples"]:
                    # SearchQuery slots require a carrier phrase.
                    self.assertIn("{query}", sample)
                    self.assertNotEqual(sample.strip(), "{query}")

    def test_each_locale_has_builtin_intents(self):
        for locale in LOCALES:
            with self.subTest(locale=locale):
                names = {i["name"] for i in self.model(locale)["intents"]}
                self.assertTrue(BUILTINS <= names)

    def test_invocation_name_rules(self):
        for locale in LOCALES:
            with self.subTest(locale=locale):
                name = self.model(locale)["invocationName"]
                self.assertEqual(name, name.lower())
                self.assertGreaterEqual(len(name.split()), 2)


if __name__ == "__main__":
    unittest.main()
