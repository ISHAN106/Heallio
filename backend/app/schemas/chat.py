from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class ConsultationSuggestion(BaseModel):
    category_name: str
    severity_level: str
    reason: str


class ChatMetricsContext(BaseModel):
    """Real recent-health context implicated in a risk-flagged reply — the
    same averages `evaluate_chat_risk` already computes, just surfaced to the
    client instead of discarded."""

    avg_sleep_hours: float | None = None
    avg_calories: float | None = None
    sleep_days_tracked: int | None = None
    diet_days_tracked: int | None = None


class ChatResponse(BaseModel):
    response: str
    escalated: bool = False
    consultation_ticket_id: int | None = None
    consultation_status: str | None = None
    doctor_id: int | None = None
    consultation_suggestion: ConsultationSuggestion | None = None
    metrics_implicated: ChatMetricsContext | None = None