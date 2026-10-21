import re
import unicodedata

# Deterministic checks on the spoken question, independent of what the model decides to say.
# They are keyword lists, so they will miss paraphrases and can over-trigger; the cost of a
# false positive is only an extra disclaimer, the cost of a miss is the model's own caution.
_EMERGENCY = {
    "es": ["suicid", "sobredosis", "quitarme la vida", "matarme", "me quiero morir", "hacerme dano", "autolesion"],
    "en": ["suicid", "overdose", "kill myself", "end my life", "want to die", "hurt myself", "self harm"],
}
_HEALTH = {
    "es": ["dosis", "dosificacion", "medicamento", "medicina", "medicinas", "pastilla", "pastillas", "tableta",
           "receta", "acetaminofen", "paracetamol", "ibuprofeno", "aspirina", "antibiotico", "sintoma",
           "sintomas", "diagnostico", "enfermedad", "tratamiento", "embarazo", "embarazada", "mg", "miligramos",
           "inyeccion", "insulina", "dolor"],
    "en": ["dose", "doses", "dosage", "medication", "medicine", "pill", "pills", "tablet", "prescription",
           "acetaminophen", "paracetamol", "ibuprofen", "aspirin", "antibiotic", "symptom", "symptoms",
           "diagnosis", "disease", "treatment", "pregnant", "pregnancy", "mg", "milligrams", "injection",
           "insulin", "pain"],
}

MESSAGES = {
    "es-US": {
        "emergency": "Lo que cuentas es importante y no puedo ayudarte con eso. Si estás en peligro o pensaste en hacerte "
                     "daño, llama ahora al 9 1 1, o al 9 8 8 para la línea de crisis, o pide ayuda a alguien cerca de ti.",
    },
    "es-ES": {
        "emergency": "Lo que cuentas es importante y no puedo ayudarte con eso. Si estás en peligro o pensaste en hacerte "
                     "daño, llama ahora al 1 1 2, o al 0 2 4 para la línea de atención a la conducta suicida, o pide "
                     "ayuda a alguien cerca de ti.",
    },
    "en-US": {
        "emergency": "What you are saying matters and I can't help with that. If you are in danger or thinking about "
                     "hurting yourself, call 9 1 1 now, or 9 8 8 for the crisis line, or ask someone near you for help.",
    },
}
DISCLAIMERS = {
    "es": "Esto es información general y no reemplaza la opinión de un médico o farmacéutico.",
    "en": "This is general information and does not replace advice from a doctor or pharmacist.",
}

HEALTH_PROMPTS = {
    "es": "La pregunta trata de salud. No indiques dosis, horarios ni tratamientos para el caso personal de quien "
          "pregunta, y no hagas diagnósticos. Puedes dar información general y pública en una o dos frases, y debes "
          "recomendar consultar a un médico o farmacéutico.",
    "en": "The question is about health. Do not give doses, schedules or treatments for the asker's personal case, "
          "and do not diagnose. You may give general public information in one or two sentences, and you must "
          "recommend asking a doctor or pharmacist.",
}


def _normalize(text):
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _language(locale):
    return "es" if (locale or "").lower().startswith("es") else "en"


def classify(query, locale):
    """Return "emergency", "health" or None."""
    lang = _language(locale)
    text = _normalize(query)
    if any(term in text for term in _EMERGENCY[lang]):
        return "emergency"
    words = set(re.findall(r"[a-z0-9]+", text))
    if any(term in words for term in _HEALTH[lang]):
        return "health"
    return None


def emergency_message(locale):
    return MESSAGES.get(locale, MESSAGES["es-US" if _language(locale) == "es" else "en-US"])["emergency"]
