from pydantic import BaseModel

class InsightItem(BaseModel):
    status: str
    message: str

class WeeklyInsightsResponse(BaseModel):
    sleep: InsightItem
    diet: InsightItem
    consistency: InsightItem
    overall_suggestion: str