# Certification checklist and device test plan

Amazon's overview page lists these areas for certification: Policy Requirements, Security Requirements, purchases (n/a), HIPAA (n/a), Advertising ID (n/a) and the required certification tests (functional and VUI/UX). Its detailed pages were not available when this was written, so every item below must be re-checked against the current Amazon pages before submitting. Nothing here has been run on a device yet.

## Metadata (`skill-package/skill.json`)
- [x] Example phrases are in each locale's language and use the invocation name (fixed in F012).
- [x] Testing instructions explain the flow and state that no account linking or purchases exist.
- [ ] Privacy policy URL added for every locale (policy text: `docs/privacy-policy.md`, still a draft with TODOs).
- [x] No brand names in the summary, description or spoken messages (replaced by "Asistente Inteligente" / "Smart Assistant").
- [x] Long descriptions written (generic, no brands, with an accuracy warning).
- [x] Icons created: `skill-package/assets/icon_108.png` and `icon_512.png` (generic robot, regenerate with `scripts/make_icons.py`).
- [ ] Confirm the category and the personal-information declaration (`usesPersonalInfo: false`) after the privacy review.
- [ ] Invocation names ("consulta inteligente", "smart answers") are free of trademarks and accepted by the console validator.

## Behaviour to confirm in the simulator and on an Echo
Run each row once per locale (es-US, es-ES, en-US). Record Pass/Fail and the date.

| # | Test | Expected | es-US | es-ES | en-US |
|---|---|---|---|---|---|
| 1 | Open the skill | Greeting and a question; session stays open | | | |
| 2 | One-shot: "ask <skill> who wrote Don Quixote" | Spoken answer, then the follow-up question | | | |
| 3 | Question starting with each word: what, who, when, how many, how much, why (es: qué, quién, cuándo, cuántos, cuánto, por qué) | Intent AskGeminiIntent matches; sensible answer | | | |
| 4 | Say "yes" after an answer | Asks for a new question | | | |
| 5 | Say "no" after an answer | Goodbye, session ends | | | |
| 6 | "Help" | Help text with an example, session open | | | |
| 7 | "Stop" and "Cancel" | Goodbye, session ends | | | |
| 8 | Nonsense speech | Fallback message, session open | | | |
| 9 | Stay silent | Reprompt, then the session ends without error | | | |
| 10 | Long-answer question ("explain the history of Rome") | Answer cut at a sentence end, not mid-word; no markdown read aloud | | | |
| 11 | Sensitive question (a harmful request) | Spoken "can't answer that"; no raw error | | | |
| 12 | Medical or legal question | Check whether the safety filters block it too often; note the behaviour | | | |
| 13 | Answer latency | Under about 5 s typically; never an Alexa error tone | | | |
| 14 | Another locale's invocation name | Not recognised (expected) | | | |
| 15 | Request from a different skill ID (call the endpoint from another skill or test event) | Rejected | | | |

## Evidence to record in the progress log
Date, device or simulator, locale, rows that failed with the exact spoken reply, and the CloudWatch log lines (they hold only locale, length, latency and error type).

## Before submitting
- [ ] F011 deployed and the endpoint set to the `:live` alias.
- [ ] F008 closed: `./scripts/smoke.sh --real` passes with the safety settings.
- [ ] Privacy policy published at a public URL and linked.
- [ ] The Amazon pages above re-read and any new rule added here.
