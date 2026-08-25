from typing import List, Optional

from pydantic import BaseModel, Field


class ScanPrediction(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)


class BodyScanAnalysisResponse(BaseModel):
    most_likely_condition: str
    confidence: float = Field(ge=0.0, le=1.0)
    predictions: List[ScanPrediction]
    urgency_level: str
    summary: str
    recommendation: str
    disclaimer: str
    body_part: Optional[str] = None
    model_version: Optional[str] = None
    training_accuracy: Optional[float] = None
