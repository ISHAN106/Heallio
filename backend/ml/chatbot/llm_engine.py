import logging

import openai
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.chat import ChatMessage
from ml.chatbot.health_context import get_health_context

logger = logging.getLogger(__name__)

FALLBACK_REPLY = (
    "I'm having trouble responding right now — please try again in a moment."
)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

SYSTEM_PROMPT_TEMPLATE = """You are Heallio's health information assistant. You are not a doctor.
- Never provide a diagnosis, prescribe medication, or give dosing instructions.
- Encourage the user to consult a licensed healthcare professional for anything serious or urgent.
- Be warm, concise, and practical about everyday health topics: sleep, diet, exercise, hydration, mental wellness, and preventive care.
- If the user's recent tracked data below looks contradictory or unhealthy (e.g. very low sleep alongside high activity, very low or very high calorie intake, patterns that conflict with basic wellness guidance), gently point out the contradiction and suggest a practical adjustment. Do this from the tracked numbers only, not assumptions.
- If the user asks about a specific interaction (food, supplement, medication, or condition), give general, well-known safety context, but explicitly say you can't check personal drug/medical interactions and to confirm with a doctor or pharmacist before acting on it.

Here is what you know about this user's recent health data (last 7 days):
- Average sleep: {avg_sleep_hours} hours/night ({sleep_days_tracked} nights tracked)
- Average calories: {avg_calories} kcal/day ({diet_days_tracked} days tracked)
"""

_client = None


def _get_client():
    global _client
    if _client is None:
        settings = get_settings()
        _client = openai.OpenAI(
            api_key=settings.GROQ_API_KEY, base_url=GROQ_BASE_URL
        )
    return _client


def _call_llm(messages: list[dict]) -> str:
    settings = get_settings()
    client = _get_client()
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        max_tokens=settings.CHAT_MAX_TOKENS,
        messages=messages,
    )
    return response.choices[0].message.content or FALLBACK_REPLY


def _build_system_prompt(db: Session, user_email: str, context: dict | None = None) -> str:
    if context is None:
        context = get_health_context(db, user_email)
    return SYSTEM_PROMPT_TEMPLATE.format(
        avg_sleep_hours=context.get("avg_sleep_hours", 0),
        sleep_days_tracked=context.get("sleep_days_tracked", 0),
        avg_calories=context.get("avg_calories", 0),
        diet_days_tracked=context.get("diet_days_tracked", 0),
    )


def _build_messages(
    system: str, history: list[ChatMessage], message: str
) -> list[dict]:
    turns = [{"role": "system", "content": system}]
    for entry in history:
        turns.append({"role": "user", "content": entry.message})
        turns.append({"role": "assistant", "content": entry.response})
    turns.append({"role": "user", "content": message})
    return turns


def generate_reply(
    message: str,
    db: Session,
    user_email: str,
    history: list[ChatMessage],
    context: dict | None = None,
) -> str:
    try:
        system = _build_system_prompt(db, user_email, context)
        messages = _build_messages(system, history, message)
        return _call_llm(messages)
    except Exception:
        logger.exception("LLM chat call failed for user %s", user_email)
        return FALLBACK_REPLY
