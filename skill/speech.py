import os
import re
from xml.sax.saxutils import escape

DEFAULT_MAX_CHARS = 600

_CODE_FENCE = re.compile(r"```[^\n]*\n?")
_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_URL = re.compile(r"(?:https?://|www\.)\S+")
_HEADING_OR_BULLET = re.compile(r"^[ \t]*(?:#{1,6}[ \t]+|[-*•+][ \t]+)", re.MULTILINE)
_EMPHASIS = re.compile(r"\*+|__+|`+|~~")


def _truncate(text, limit):
    if len(text) <= limit:
        return text
    cut = text[:limit]
    # A terminator only ends a sentence when followed by whitespace or the end of the full text.
    ends = [
        i for i, ch in enumerate(cut)
        if ch in ".!?" and (i + 1 == len(text) or text[i + 1].isspace())
    ]
    if ends:
        return cut[: ends[-1] + 1]
    if text[limit].isspace():
        return cut
    return cut.rsplit(" ", 1)[0] if " " in cut else cut


def to_speech(text, max_chars=None):
    """Turn model output into plain text that is safe inside Alexa SSML."""
    if max_chars is None:
        max_chars = int(os.environ.get("SPEECH_MAX_CHARS", DEFAULT_MAX_CHARS))
    text = _CODE_FENCE.sub("", text)
    text = _LINK.sub(r"\1", text)
    text = _URL.sub("", text)
    text = _HEADING_OR_BULLET.sub("", text)
    text = _EMPHASIS.sub("", text)
    text = " ".join(text.split())
    return escape(_truncate(text, max_chars))
