import os

# How many previous question/answer pairs are sent to the model; 0 turns the context off.
DEFAULT_CONTEXT_TURNS = 4
MAX_CONTEXT_TURNS = 10
# Stored turns are shortened to bound the prompt size and the Alexa response size.
MAX_HISTORY_QUERY_CHARS = 500
MAX_HISTORY_ANSWER_CHARS = 300
HISTORY_KEY = "history"


def context_turns():
    raw = os.environ.get("CONTEXT_TURNS")
    if raw is None:
        return DEFAULT_CONTEXT_TURNS
    try:
        return min(MAX_CONTEXT_TURNS, max(0, int(raw)))
    except ValueError:
        return DEFAULT_CONTEXT_TURNS


def recall(session_attributes):
    """Previous turns to send to the model, oldest first.

    Session attributes can be edited in the simulator or by anyone who can invoke the Lambda,
    so anything that is not a well-formed turn is dropped instead of trusted.
    """
    turns = context_turns()
    stored = session_attributes.get(HISTORY_KEY)
    if not turns or not isinstance(stored, list):
        return []
    clean = []
    for turn in stored[-turns:]:
        if (isinstance(turn, dict) and isinstance(turn.get("q"), str) and isinstance(turn.get("a"), str)
                and turn["q"].strip() and turn["a"].strip()):
            clean.append({"q": turn["q"][:MAX_HISTORY_QUERY_CHARS], "a": turn["a"][:MAX_HISTORY_ANSWER_CHARS],
                          "h": turn.get("h") is True})
    return clean


def remember(session_attributes, query, answer, health=False):
    """Store the turn in the Alexa session attributes (alive only while the session lasts).

    "h" marks a health turn: while it stays inside the window, the health guardrail keeps applying.
    """
    turns = context_turns()
    if not turns:
        session_attributes.pop(HISTORY_KEY, None)
        return
    history = recall(session_attributes)
    history.append({"q": query[:MAX_HISTORY_QUERY_CHARS], "a": answer[:MAX_HISTORY_ANSWER_CHARS], "h": health})
    session_attributes[HISTORY_KEY] = history[-turns:]


def has_health_turn(history):
    return any(turn.get("h") for turn in history)
