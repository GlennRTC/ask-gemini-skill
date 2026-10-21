import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skill import context  # noqa: E402
from skill.gemini import ask_gemini  # noqa: E402
from skill.guardrails import DISCLAIMERS  # noqa: E402
from test_handlers import intent, lambda_handler, speech  # noqa: E402


def ask(query, attributes=None, locale="en-US"):
    slots = {"query": {"name": "query", "value": query, "confirmationStatus": "NONE"}}
    request = intent("AskGeminiIntent", locale, slots)
    request["session"]["attributes"] = attributes or {}
    return request


class ContextUnitTest(unittest.TestCase):
    def env(self, **values):
        patcher = mock.patch.dict(os.environ, values, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_window_keeps_only_the_last_n_turns(self):
        self.env(CONTEXT_TURNS="2")
        session = {}
        for i in range(4):
            context.remember(session, f"q{i}", f"a{i}")
        self.assertEqual([t["q"] for t in context.recall(session)], ["q2", "q3"])

    def test_zero_turns_disables_context(self):
        self.env(CONTEXT_TURNS="0")
        session = {}
        context.remember(session, "q", "a")
        self.assertEqual(context.recall(session), [])
        self.assertNotIn(context.HISTORY_KEY, session)

    def test_default_and_bad_values(self):
        self.env()
        self.assertEqual(context.context_turns(), context.DEFAULT_CONTEXT_TURNS)
        self.env(CONTEXT_TURNS="many")
        self.assertEqual(context.context_turns(), context.DEFAULT_CONTEXT_TURNS)
        self.env(CONTEXT_TURNS="-3")
        self.assertEqual(context.context_turns(), 0)

    def test_stored_answers_are_shortened(self):
        self.env(CONTEXT_TURNS="1")
        session = {}
        context.remember(session, "q", "x" * 1000)
        self.assertEqual(len(session[context.HISTORY_KEY][0]["a"]), context.MAX_HISTORY_ANSWER_CHARS)

    def test_history_becomes_alternating_roles_before_the_current_question(self):
        seen = {}

        def generate_content(**kwargs):
            seen.update(kwargs)
            return mock.Mock(text="ok", prompt_feedback=None)

        client = mock.Mock(models=mock.Mock(generate_content=generate_content))
        ask_gemini("and when was he born", "en-US", client=client,
                   history=[{"q": "who wrote Don Quixote", "a": "Cervantes.", "h": False}])
        roles = [c.role for c in seen["contents"]]
        self.assertEqual(roles, ["user", "model", "user"])
        self.assertEqual(seen["contents"][-1].parts[0].text, "and when was he born")


class ContextHandlerTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != "CONTEXT_TURNS"}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_first_question_sends_no_history_and_stores_the_turn(self):
        with mock.patch("skill.lambda_function.ask_gemini", return_value="Cervantes.") as fake:
            resp = lambda_handler(ask("who wrote Don Quixote"), None)
        fake.assert_called_once_with("who wrote Don Quixote", "en-US")
        self.assertEqual(resp["sessionAttributes"]["history"], [{"q": "who wrote Don Quixote", "a": "Cervantes.", "h": False}])

    def test_follow_up_receives_the_history(self):
        attrs = {"history": [{"q": "who wrote Don Quixote", "a": "Cervantes."}]}
        with mock.patch("skill.lambda_function.ask_gemini", return_value="1547.") as fake:
            resp = lambda_handler(ask("and when was he born", attrs), None)
        fake.assert_called_once_with("and when was he born", "en-US",
                                     history=[{"q": "who wrote Don Quixote", "a": "Cervantes.", "h": False}])
        self.assertEqual(len(resp["sessionAttributes"]["history"]), 2)

    def test_failures_and_emergencies_are_not_remembered(self):
        from skill.gemini import GeminiError

        with mock.patch("skill.lambda_function.ask_gemini", side_effect=GeminiError("timeout")):
            resp = lambda_handler(ask("who wrote Don Quixote"), None)
        self.assertNotIn("history", resp["response"].get("sessionAttributes", {}) or resp.get("sessionAttributes", {}))
        with mock.patch("skill.lambda_function.ask_gemini") as fake:
            resp = lambda_handler(ask("I want to die"), None)
        fake.assert_not_called()
        self.assertNotIn("history", resp.get("sessionAttributes", {}))

    def test_health_guardrail_lasts_while_the_health_turn_is_in_the_window(self):
        with mock.patch("skill.lambda_function.ask_gemini", return_value="Ask a doctor.") as fake:
            attrs = lambda_handler(ask("paracetamol dose"), None)["sessionAttributes"]
            replies = []
            for query in ("and for a child", "capital of France", "capital of Spain", "capital of Italy"):
                resp = lambda_handler(ask(query, attrs), None)
                attrs = resp["sessionAttributes"]
                replies.append(speech(resp))
        # Window of 4: the health turn is replayed for the next four questions, so all keep the guard.
        self.assertTrue(all(DISCLAIMERS["en"] in r for r in replies))
        self.assertIn("extra_instruction", fake.call_args_list[-1].kwargs)
        with mock.patch("skill.lambda_function.ask_gemini", return_value="Rome.") as fake:
            resp = lambda_handler(ask("capital of Portugal", attrs), None)
        # The health turn has now left the window.
        self.assertNotIn(DISCLAIMERS["en"], speech(resp))

    def test_malformed_attributes_are_ignored(self):
        bad = [None, "text", {"q": "x"}, [1, 2], [{"q": 1, "a": "x"}], [{"q": "x", "a": ""}], {"history": 5}]
        for value in bad:
            with self.subTest(value=value):
                with mock.patch("skill.lambda_function.ask_gemini", return_value="ok") as fake:
                    resp = lambda_handler(ask("who wrote Don Quixote", {"history": value}), None)
                fake.assert_called_once_with("who wrote Don Quixote", "en-US")
                self.assertIn("ok", speech(resp))

    def test_turns_are_capped(self):
        with mock.patch.dict(os.environ, {"CONTEXT_TURNS": "999"}):
            self.assertEqual(context.context_turns(), context.MAX_CONTEXT_TURNS)


if __name__ == "__main__":
    unittest.main()
