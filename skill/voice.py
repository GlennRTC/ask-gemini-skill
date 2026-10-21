from ask_sdk_core.dispatch_components import AbstractResponseInterceptor

# Amazon Polly voice per locale; an empty value keeps Alexa's own voice. A voice must match its
# locale's language, and Alexa's policy says not to tell users the Polly voice name.
VOICES = {
    "es-US": "Miguel",
    "es-ES": "Enrique",
    "en-US": "Matthew",
}


def with_voice(ssml, voice):
    if not voice or not ssml.startswith("<speak>") or "<voice" in ssml:
        return ssml
    return f'<speak><voice name="{voice}">{ssml[len("<speak>"):-len("</speak>")]}</voice></speak>'


class VoiceInterceptor(AbstractResponseInterceptor):
    """Wraps every spoken text and reprompt of the response in the locale's voice."""

    def process(self, handler_input, response):
        if response is None:
            return
        voice = VOICES.get(handler_input.request_envelope.request.locale or "")
        speech = response.output_speech
        if speech is not None and getattr(speech, "ssml", None):
            speech.ssml = with_voice(speech.ssml, voice)
        reprompt = response.reprompt.output_speech if response.reprompt else None
        if reprompt is not None and getattr(reprompt, "ssml", None):
            reprompt.ssml = with_voice(reprompt.ssml, voice)
