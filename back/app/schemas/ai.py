from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class AIPredictionRequest(BaseModel):
    period_days: int = Field(..., ge=1, le=30, description="На сколько дней вперёд строим прогноз")
    categories: Optional[List[str]] = Field(
        default=None,
        description="Какие категории товаров учитывать (если None — все)"
    )


class ProductPrediction(BaseModel):
    product_id: str
    category: Optional[str] = None
    expected_demand: int  # прогнозируемый спрос за период (шт)
    expected_stockout_in_days: Optional[float] = None  # через сколько дней кончится склад


class AIPredictionResponse(BaseModel):
    predictions: List[ProductPrediction]
    confidence: float = Field(..., ge=0.0, le=1.0)
