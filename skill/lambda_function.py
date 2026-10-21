import logging

from ask_sdk_core.dispatch_components import AbstractExceptionHandler, AbstractRequestHandler
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_intent_name, is_request_type

from .gemini import GeminiError, ask_gemini
from .secrets import SecretError
from .speech import to_speech

logger = logging.getLogger(__name__)

# Spoken strings per language; unknown locales fall back to English.
MESSAGES = {
    "es": {
        "welcome": "Hola, ¿qué quieres saber?",
        "welcome_reprompt": "Puedes hacerme cualquier pregunta. ¿Qué quieres saber?",
        "help": "Dime tu pregunta, por ejemplo: quién escribió Don Quijote.",
        "fallback": "No te entendí. ¿Qué quieres saber?",
        "bye": "Hasta luego.",
        "more": "¿Quieres preguntar algo más?",
        "error": "Hubo un problema al consultar. ¿Quieres intentarlo de nuevo?",
        "error_timeout": "Gemini tardó demasiado en responder. ¿Quieres intentarlo de nuevo?",
        "error_quota": "Se alcanzó el límite de consultas por ahora. Inténtalo de nuevo más tarde.",
        "error_blocked": "No puedo responder esa pregunta. ¿Quieres preguntar otra cosa?",
    },
    "en": {
        "welcome": "Hi, what would you like to know?",
        "welcome_reprompt": "You can ask me anything. What would you like to know?",
        "help": "Tell me your question, for example: who wrote Don Quixote.",
        "fallback": "Sorry, I didn't get that. What would you like to know?",
        "bye": "Goodbye.",
        "more": "Would you like to ask something else?",
        "error": "There was a problem answering. Would you like to try again?",
        "error_timeout": "Gemini took too long to answer. Would you like to try again?",
        "error_quota": "The query limit has been reached for now. Please try again later.",
        "error_blocked": "I can't answer that question. Would you like to ask something else?",
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
            kind = getattr(exc, "kind", type(exc).__name__)
            logger.warning("gemini_failure kind=%s status=%s", kind, getattr(exc, "status", None))
            message = m.get(f"error_{kind}", m["error"])
            return rb.speak(message).ask(message).response
        spoken = to_speech(answer)
        if not spoken:
            return rb.speak(m["error"]).ask(m["error"]).response
        # Each question is independent (stateless v1); the follow-up only keeps the session open.
        return rb.speak(f"{spoken} {m['more']}").ask(m["more"]).response


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


class YesIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.YesIntent")(handler_input)

    def handle(self, handler_input):
        m = messages_for(handler_input)
        return handler_input.response_builder.speak(m["welcome"]).ask(m["welcome_reprompt"]).response


class StopCancelIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return any(
            is_intent_name(name)(handler_input)
            for name in ("AMAZON.StopIntent", "AMAZON.CancelIntent", "AMAZON.NoIntent")
        )

    def handle(self, handler_input):
        m = messages_for(handler_input)
        return handler_input.response_builder.speak(m["bye"]).set_should_end_session(True).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        # Only the exception type is logged: messages may include the user's query.
        logger.error("unhandled_exception type=%s", type(exception).__name__)
        m = messages_for(handler_input)
        return handler_input.response_builder.speak(m["error"]).ask(m["error"]).response


sb = SkillBuilder()
sb.add_exception_handler(CatchAllExceptionHandler())
for handler in (
    LaunchRequestHandler(),
    AskGeminiIntentHandler(),
    YesIntentHandler(),
    HelpIntentHandler(),
    FallbackIntentHandler(),
    StopCancelIntentHandler(),
    SessionEndedRequestHandler(),
):
    sb.add_request_handler(handler)

lambda_handler = sb.lambda_handler()
