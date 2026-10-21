# ADR-004: Short-term context kept in Alexa session attributes
**Fecha:** 2026-10-21
**Estado:** aceptado

**Contexto:**
Follow-up questions ("and when was he born?") need the previous turns. v1 was stateless and the owner asked for a context window configurable from the code.

**Decisión:**
Keep the last `CONTEXT_TURNS` question/answer pairs (default 4, hard maximum 10, 0 disables) in Alexa session attributes and replay them to the model as alternating user/model turns (`skill/context.py`). Nothing is stored by the skill: the attributes travel in each Alexa request and die with the session. Stored turns are cut (500 chars question, 300 answer) and malformed attributes are dropped on read. A turn that was a health question is marked, and while it stays inside the window every answer keeps the health guardrail and disclaimer. Emergency, error and blocked turns are never stored.

**Alternativas consideradas:**
- DynamoDB history across sessions — needs storage, retention rules and a privacy review; not needed for follow-ups inside one conversation.
- No context — simplest, but follow-ups fail.

**Consecuencias:**
- Follow-ups work with no new infrastructure or dependency.
- Earlier questions, including health ones, are sent to Google on every call and held in Alexa's session data (Amazon's own retention applies); the privacy policy says so.
- The emergency check looks only at the current sentence: a keywordless follow-up to a health turn ("and if I take 30 of those?") is not treated as an emergency. This is a known limitation of keyword lists.
- Session attributes can be edited in the simulator or by anyone who can invoke the Lambda; the replay is treated as untrusted input, and the skill-ID check is the real boundary.
- A redeploy without `CONTEXT_TURNS` resets the value to the code default.

**Referencias:** F014.
