DANGEROUS_MEDICAL_KEYWORDS = [
    "cancer",
    "tumor",
    "malaria",
    "typhoid",
    "medicine",
    "prescription",
    "dose",
    "antibiotic",
    "steroid",
    "drug dosage",
]

CRISIS_KEYWORDS = [
    "suicide",
    "suicidal",
    "kill myself",
    "self harm",
    "hurt myself",
    "overdose",
    "can't breathe",
    "cannot breathe",
    "severe chest pain",
    "unconscious",
]


import re


def _collapse(text: str) -> str:
    """Strip everything but letters/digits so spacing/punctuation obfuscation
    (e.g. "s.u.i.c.i.d.e", "kill  myself") still matches."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _contains_any(message: str, keywords: list[str]) -> bool:
    # ponytail: keyword+normalization heuristic, not a real moderation model.
    # Catches spacing/punctuation evasion but not paraphrase/misspelling;
    # upgrade to an LLM/moderation classifier if evasion becomes a problem.
    lowered = message.lower()
    collapsed = _collapse(message)
    for keyword in keywords:
        if keyword in lowered or _collapse(keyword) in collapsed:
            return True
    return False


def is_crisis_message(message: str) -> bool:
    """Detect potentially life-threatening or self-harm related prompts."""
    return _contains_any(message, CRISIS_KEYWORDS)


def is_safe(message: str) -> bool:
    """Return False for unsafe medical or crisis requests."""
    if is_crisis_message(message):
        return False
    if _contains_any(message, DANGEROUS_MEDICAL_KEYWORDS):
        return False
    return True


def get_safety_message(message: str) -> str:
    """Return context-specific safety guidance."""
    if is_crisis_message(message):
        return (
            "This sounds urgent. Please contact emergency services immediately or go to the "
            "nearest emergency department. If you may harm yourself, please call your local "
            "crisis helpline right now and reach out to someone nearby."
        )

    return (
        "I cannot provide diagnosis, prescriptions, or medication dosing. Please consult "
        "a licensed healthcare professional."
    )