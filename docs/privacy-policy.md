# Privacy policy (DRAFT)

> Draft for the skill owner to review. Alexa requires a publicly reachable privacy policy URL to publish the skill; host this text (after legal review) and put the URL in `skill-package/skill.json`. Items marked TODO need a decision from the owner.

## What the skill processes
- The text of the question you say after the invocation phrase, as transcribed by Alexa.
- Your Alexa locale (for example es-US) to choose the answer language.

## Where it goes
- The question text is sent to Google's Gemini API to generate the answer, which Alexa reads back to you.
- The skill runs on AWS Lambda. The API key is kept in AWS Systems Manager Parameter Store.

## What the skill stores
- Nothing about your questions or answers. The skill has no database and keeps no conversation history; each question is independent.
- Logs record only metadata: locale, answer length, response time and error type. They never include the question or the answer. AWS keeps these logs according to its CloudWatch retention setting (14 days, set by `scripts/deploy.sh`).
- The skill does not request or use your name, email, address or device location.

## Third parties
- Google processes the question under its own terms. TODO: confirm, against Google's current Gemini API terms, whether the plan in use may retain prompts or use them for model training, and state it here.

## Contact and changes
- TODO: owner name and contact email.
- TODO: date of the last update.
