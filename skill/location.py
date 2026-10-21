import logging
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urlsplit

# Pinned with hashes in requirements.txt; ask-sdk-core already depends on it.
import requests

logger = logging.getLogger(__name__)

PERMISSION = "read::alexa:device:all:address:country_and_postal_code"
# Hard wall-clock budget for the whole lookup (DNS, connect and read), enforced with a worker thread
# because requests' timeouts apply per phase. It runs before the model call.
DEADLINE_S = 1.5
HTTP_TIMEOUT = (0.5, 1.0)
# The bearer token from the request is only ever sent to Amazon's own API hosts.
ALLOWED_API_HOSTS = {"api.amazonalexa.com", "api.eu.amazonalexa.com", "api.fe.amazonalexa.com"}
POSTAL_FORMATS = {"US": r"\d{5}(-\d{4})?", "ES": r"\d{5}"}
# Alexa returns this Seattle code in North America when the user never entered an address.
US_PLACEHOLDER = "98109"

# The postal code is only fetched (and sent to the model) when the question asks about the user's
# surroundings. Generic "where" questions ("where did Cervantes die") must not trigger it.
_NEAR_WORDS = {
    "es": ["cerca", "cercano", "cercana", "cercanos", "cercanas", "zona", "barrio", "alrededor", "alrededores"],
    "en": ["near", "nearby", "nearest", "neighborhood", "neighbourhood"],
}
_NEAR_PHRASES = {
    "es": ["mi ciudad", "mi pueblo", "por aqui", "aqui cerca"],
    "en": ["my city", "my town", "my area", "around here", "near here", "around me"],
}

MESSAGES = {
    "es": "Si quieres sugerencias de tu zona, da permiso de código postal en la app de Alexa; te envié una tarjeta.",
    "en": "If you want suggestions for your area, allow postal code access in the Alexa app; I sent you a card.",
}

PROMPTS = {
    "es": "El usuario está en el código postal {postal} de {country}. Úsalo solo si la pregunta trata de lugares o "
          "de su zona, y no repitas el código postal en la respuesta. No tienes datos en tiempo real: no afirmes "
          "horarios ni si un lugar sigue abierto, y sugiere comprobarlo.",
    "en": "The user is in postal code {postal}, {country}. Use it only if the question is about places or their "
          "area, and do not repeat the postal code in your answer. You have no real-time data: do not state "
          "opening hours or whether a place is still open, and suggest checking.",
}


def _language(locale):
    return "es" if (locale or "").lower().startswith("es") else "en"


def _normalize(text):
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def is_place_question(query, locale):
    lang = _language(locale)
    text = _normalize(query)
    words = set(re.findall(r"[a-z0-9]+", text))
    return any(word in words for word in _NEAR_WORDS[lang]) or any(p in text for p in _NEAR_PHRASES[lang])


def _lookup(endpoint, device_id, token):
    url = f"{endpoint}/v1/devices/{quote(device_id, safe='')}/settings/address/countryAndPostalCode"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=HTTP_TIMEOUT,
                        allow_redirects=False)
    if resp.status_code == 403:
        return "denied", None, None
    if resp.status_code != 200:
        return "none", None, None
    body = resp.json()
    country = str(body.get("countryCode") or "").strip().upper()
    postal = str(body.get("postalCode") or "").strip()
    # Only codes in the expected national format reach the prompt, so the response cannot inject text.
    pattern = POSTAL_FORMATS.get(country)
    if not pattern or not re.fullmatch(pattern, postal) or (country == "US" and postal.startswith(US_PLACEHOLDER)):
        return "none", None, None
    return "ok", country, postal


def postal_code(request_envelope):
    """Return ("ok", country, postal), ("denied", None, None) or ("none", None, None).

    Anything other than a missing permission degrades to "none": the answer goes on without location.
    """
    system = request_envelope.context.system if request_envelope.context else None
    if system is None:
        return "none", None, None
    permissions = getattr(system.user, "permissions", None) if system.user else None
    if not getattr(permissions, "consent_token", None):
        return "denied", None, None  # no consent yet, no need to ask Amazon
    token = system.api_access_token
    endpoint = (system.api_endpoint or "").rstrip("/")
    device_id = system.device.device_id if system.device else None
    parts = urlsplit(endpoint)
    if not (token and device_id and parts.scheme == "https" and parts.hostname in ALLOWED_API_HOSTS
            and not parts.path and not parts.port):
        return "none", None, None

    executor = ThreadPoolExecutor(max_workers=1)
    try:
        return executor.submit(_lookup, endpoint, device_id, token).result(timeout=DEADLINE_S)
    except Exception as exc:
        # Only the type: request errors can carry the URL, which includes the device id.
        logger.warning("location_lookup_failed type=%s", type(exc).__name__)
        return "none", None, None
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def prompt(locale, country, postal):
    return PROMPTS[_language(locale)].format(postal=postal, country=country)


def scrub(text, postal):
    """Remove the postal code from text that will be stored or replayed."""
    return text.replace(postal, "").replace("  ", " ") if postal else text


def permission_note(locale):
    return MESSAGES[_language(locale)]
