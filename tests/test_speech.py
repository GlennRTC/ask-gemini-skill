import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skill.speech import to_speech  # noqa: E402


class SpeechTest(unittest.TestCase):
    def test_strips_markdown(self):
        text = "# Title\n**Bold** and *italic* with `code`.\n- one\n- two\n"
        self.assertEqual(to_speech(text), "Title Bold and italic with code. one two")

    def test_links_keep_text_and_urls_are_dropped(self):
        text = "See [the docs](https://example.com/a) or https://example.com/b now."
        self.assertEqual(to_speech(text), "See the docs or now.")

    def test_code_fence_markers_removed(self):
        self.assertEqual(to_speech("```python\nprint(1)\n```"), "print(1)")

    def test_escapes_ssml_characters(self):
        self.assertEqual(to_speech("R&D <audio src='x'/> 3 > 2"), "R&amp;D &lt;audio src='x'/&gt; 3 &gt; 2")

    def test_truncates_at_sentence_boundary(self):
        text = "First one. Second one is here. Third one goes beyond."
        self.assertEqual(to_speech(text, max_chars=35), "First one. Second one is here.")

    def test_does_not_cut_inside_a_decimal(self):
        self.assertEqual(to_speech("Pi is 3.14159 roughly speaking", max_chars=10), "Pi is")

    def test_no_sentence_end_cuts_at_word(self):
        self.assertEqual(to_speech("alpha beta gamma delta", max_chars=13), "alpha beta")

    def test_short_text_unchanged_and_empty_ok(self):
        self.assertEqual(to_speech("Hello."), "Hello.")
        self.assertEqual(to_speech("  **  "), "")

    def test_truncation_happens_before_escaping(self):
        self.assertEqual(to_speech("a & b & c", max_chars=5), "a &amp; b")


if __name__ == "__main__":
    unittest.main()
