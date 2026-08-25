from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FoodPrediction(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)


class MicronutrientValue(BaseModel):
    name: str
    amount: str


class FoodScanAnalysisResponse(BaseModel):
    meal_type: str
    predicted_food: str
    amount: str
    serving_size: str
    estimated_grams: float = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    calories: int = Field(ge=0)
    carbs: int = Field(ge=0)
    protein: int = Field(ge=0)
    fat: int = Field(ge=0)
    fiber: int = Field(ge=0)
    sugar: int = Field(ge=0)
    micronutrients: list[MicronutrientValue]
    contents: list[str]
    predictions: list[FoodPrediction]
    notes: str
    model_version: str
    training_accuracy: float | None = None
    scanned_at: datetime
