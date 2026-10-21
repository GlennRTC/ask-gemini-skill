# Certification notes for Alexa

Technical points that affect certification, collected during F008. The full checklist and device tests are tracked in F012.

- **Invocation names** are provisional ("consulta inteligente", "smart answers"). Avoid third-party trademarks such as "Gemini" in the invocation name and skill name unless Google authorises it.
- **Privacy policy URL** is mandatory for publishing; see `docs/privacy-policy.md` (draft).
- **Personal information flag:** `usesPersonalInfo` is `false` in `skill.json` because the skill reads no account data. Re-check this if the privacy review concludes that spoken questions count as personal data to declare.
- **Skill ID verification:** the handler rejects requests whose application ID differs from `ALEXA_SKILL_ID`, and refuses to run at all when the variable is missing (local runs must set `ALLOW_NO_SKILL_ID=1`). F011 must set the variable and restrict the Lambda trigger to the same skill ID.
- **Content:** Gemini safety filters are set to block medium-and-above harm in four categories, and a blocked answer gets a spoken "I can't answer that" message. Alexa's content policy for the chosen category must still be reviewed in F012.
- **Answers read by voice** come from a generative model and may be wrong; consider a short disclaimer in the skill description.
- **Logging:** the privacy policy promises that logs never include questions or answers. Do not enable DEBUG logging for `ask_sdk`, `httpx` or `google.genai` in Lambda (F011 must keep them at WARNING or higher).
- **Safety categories:** civic integrity is not set because support in the chosen model was not verified; measure false positives (medical or legal questions) in the real smoke test.
