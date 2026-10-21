import logging
import os
import time

from ask_sdk_core.dispatch_components import AbstractExceptionHandler, AbstractRequestHandler
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_intent_name, is_request_type
from ask_sdk_model.ui import AskForPermissionsConsentCard

from . import context, location
from .gemini import DEFAULT_TIMEOUT_S as GEMINI_TIMEOUT_S
from .gemini import GeminiError, ask_gemini
from .guardrails import DISCLAIMERS, HEALTH_PROMPTS, classify, emergency_message
from .secrets import SecretError
from .speech import to_speech
from .voice import VoiceInterceptor

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Location lookup plus model call must leave room for a cold start inside Alexa's ~8 s.
LOCATION_TOTAL_BUDGET_S = 5.5

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
        "error_timeout": "El asistente tardó demasiado en responder. ¿Quieres intentarlo de nuevo?",
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
        "error_timeout": "The assistant took too long to answer. Would you like to try again?",
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
        locale = handler_input.request_envelope.request.locale
        session = handler_input.attributes_manager.session_attributes
        lang = "es" if (locale or "").lower().startswith("es") else "en"
        topic = classify(query, locale)
        previous = context.recall(session)
        if topic == "emergency":
            logger.info("guardrail topic=emergency locale=%s", locale)
            return rb.speak(emergency_message(locale)).set_should_end_session(True).response
        raw_topic = topic
        if topic is None and context.has_health_turn(previous):
            topic = "health"  # a health question still inside the window keeps the guardrail
        started = time.monotonic()
        instructions = []
        if topic == "health":
            instructions.append(HEALTH_PROMPTS[lang])
        place_status, postal = None, None
        if location.is_place_question(query, locale):
            place_status, country, postal = location.postal_code(handler_input.request_envelope)
            logger.info("location status=%s", place_status)  # never the code itself
            if place_status == "ok":
                instructions.append(location.prompt(locale, country, postal))
        try:
            options = {}
            if instructions:
                options["extra_instruction"] = " ".join(instructions)
            if previous:
                options["history"] = previous
            if place_status is not None:
                # The location lookup already spent part of the time Alexa allows.
                spent = time.monotonic() - started
                options["timeout_s"] = max(2.5, min(GEMINI_TIMEOUT_S, LOCATION_TOTAL_BUDGET_S - spent))
            answer = ask_gemini(query, locale, **options)
        except (GeminiError, SecretError) as exc:
            # Log only the error kind: the query may hold personal data.
            kind = getattr(exc, "kind", type(exc).__name__)
            logger.warning("gemini_failure kind=%s status=%s", kind, getattr(exc, "status", None))
            message = m.get(f"error_{kind}", m["error"])
            return rb.speak(message).ask(message).response
        # Metadata only: the query and the answer may contain personal data.
        logger.info("answer_ok locale=%s topic=%s chars=%d latency_ms=%d", locale, topic, len(answer),
                    (time.monotonic() - started) * 1000)
        spoken = to_speech(answer)
        if not spoken:
            return rb.speak(m["error"]).ask(m["error"]).response
        # Only a genuine health question is marked; inherited ones must not keep the guard alive forever.
        # The model is told not to repeat the postal code; scrub it anyway before it is replayed.
        context.remember(session, query, location.scrub(answer, postal), health=raw_topic == "health")
        if topic == "health":
            spoken = f"{spoken} {DISCLAIMERS[lang]}"
        if place_status == "denied":
            rb.set_card(AskForPermissionsConsentCard(permissions=[location.PERMISSION]))
            spoken = f"{spoken} {location.permission_note(locale)}"
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
        response = handler_input.response_builder.speak(m["error"]).ask(m["error"]).response
        # Response interceptors do not run on the exception path, so apply the voice here too.
        VoiceInterceptor().process(handler_input, response)
        return response


sb = SkillBuilder()
sb.add_exception_handler(CatchAllExceptionHandler())
sb.add_global_response_interceptor(VoiceInterceptor())
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

_dispatch = sb.lambda_handler()


def lambda_handler(event, context):
    """Reject requests that do not come from our skill before doing any work."""
    expected = os.environ.get("ALEXA_SKILL_ID")
    if not expected:
        # Fail closed: without the ID anyone who knows the endpoint could spend the API key.
        # Local runs opt out explicitly.
        if os.environ.get("ALLOW_NO_SKILL_ID") != "1":
            raise RuntimeError("ALEXA_SKILL_ID is not configured")
    else:
        try:
            actual = event["context"]["System"]["application"]["applicationId"]
        except (KeyError, TypeError):
            actual = None
        if actual != expected:
            raise ValueError("Invalid skill id")
    return _dispatch(event, context)
