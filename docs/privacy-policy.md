# Privacy policy (DRAFT)

> Draft for the skill owner to review. Alexa requires a publicly reachable privacy policy URL to publish the skill; host this text (after legal review) and put the URL in `skill-package/skill.json`. Items marked TODO need a decision from the owner.

## What the skill processes
- The text of the question you say after the invocation phrase, as transcribed by Alexa.
- Your Alexa locale (for example es-US) to choose the answer language.

## Where it goes
- The question text, together with the previous turns of the same session, is sent to Google's Gemini API to generate the answer, which Alexa reads back to you.
- The skill runs on AWS Lambda. The API key is kept in AWS Systems Manager Parameter Store.

## What the skill stores
- The skill has no database and writes nothing to disk. To understand follow-up questions, the last few questions and answers of the current Alexa session (4 by default) are kept in Alexa's session attributes and sent again to the model with each new question. Alexa, not the skill, controls how long session data lives and what Amazon retains under its own policy; the skill does not keep it after the session ends.
- This includes health-related questions if you ask them. Do not say anything you would not want Google to receive.
- Logs record only metadata: locale, topic category (for example "health"), answer length, response time and error type. They never include the question or the answer. AWS keeps these logs for 14 days (set by `scripts/deploy.sh`).
- The skill does not request or use your name, email, address or device location.

## Third parties
- Google processes the question under its own terms. TODO: confirm, against Google's current Gemini API terms, whether the plan in use may retain prompts or use them for model training, and state it here.

## Contact and changes
- TODO: owner name and contact email.
- TODO: date of the last update.
