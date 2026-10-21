import logging
from xml.sax.saxutils import escape

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_intent_name, is_request_type

from .gemini import GeminiError, ask_gemini
from .secrets import SecretError

logger = logging.getLogger(__name__)

# Spoken strings per language; unknown locales fall back to English.
MESSAGES = {
    "es": {
        "welcome": "Hola, ¿qué quieres saber?",
        "welcome_reprompt": "Puedes hacerme cualquier pregunta. ¿Qué quieres saber?",
        "help": "Dime tu pregunta, por ejemplo: quién escribió Don Quijote.",
        "fallback": "No te entendí. ¿Qué quieres saber?",
        "bye": "Hasta luego.",
        "error": "Hubo un problema al consultar. ¿Quieres intentarlo de nuevo?",
    },
    "en": {
        "welcome": "Hi, what would you like to know?",
        "welcome_reprompt": "You can ask me anything. What would you like to know?",
        "help": "Tell me your question, for example: who wrote Don Quixote.",
        "fallback": "Sorry, I didn't get that. What would you like to know?",
        "bye": "Goodbye.",
        "error": "There was a problem answering. Would you like to try again?",
    },
}


def messages_for(handler_input):
    locale = handler_input.request_envelope.request.locale or "en-US"
    return MESSAGES.get(locale.split("-")[0].lower(), MESSAGES["en"])


class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        m = messages_for(handler_input)
        return handler_input.response_builder.speak(m["welcome"]).ask(m["welcome_reprompt"]).response


class AskGeminiIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AskGeminiIntent")(handler_input)

    def handle(self, handler_input):
        m = messages_for(handler_input)
        rb = handler_input.response_builder
        slot = (handler_input.request_envelope.request.intent.slots or {}).get("query")
        query = slot.value if slot else None
        if not query:
            return rb.speak(m["fallback"]).ask(m["fallback"]).response
        try:
            answer = ask_gemini(query, handler_input.request_envelope.request.locale)
        except (GeminiError, SecretError) as exc:
            # Log only the error kind: the query may hold personal data.
            logger.warning("gemini_failure kind=%s", getattr(exc, "kind", type(exc).__name__))
            return rb.speak(m["error"]).ask(m["error"]).response
        return rb.speak(escape(answer)).ask(m["welcome_reprompt"]).response


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        m = messages_for(handler_input)
        return handler_input.response_builder.speak(m["help"]).ask(m["help"]).response


class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        m = messages_for(handler_input)
        return handler_input.response_builder.speak(m["fallback"]).ask(m["fallback"]).response


class StopCancelIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.StopIntent")(handler_input) or is_intent_name(
            "AMAZON.CancelIntent"
        )(handler_input)

    def handle(self, handler_input):
        m = messages_for(handler_input)
        return handler_input.response_builder.speak(m["bye"]).set_should_end_session(True).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


sb = SkillBuilder()
for handler in (
    LaunchRequestHandler(),
    AskGeminiIntentHandler(),
    HelpIntentHandler(),
    FallbackIntentHandler(),
    StopCancelIntentHandler(),
    SessionEndedRequestHandler(),
):
    sb.add_request_handler(handler)

lambda_handler = sb.lambda_handler()
