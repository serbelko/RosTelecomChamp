from __future__ import annotations
from typing import List, Optional
from random import uniform

from app.repo.product import ProductRepository
from app.schemas.ai import (
    AIPredictionRequest,
    AIPredictionResponse,
    ProductPrediction,
)


class AIService:
    def __init__(self, product_repo: ProductRepository):
        self.product_repo = product_repo

    async def predict(self, req: AIPredictionRequest) -> AIPredictionResponse:
        """
        Простейший мок предикта.
        В реальности здесь должна быть модель времени/спроса,
        но в прототипе мы берём товары и делаем псевдопрогноз.
        """

        # загружаем товары из БД
        # можно потом фильтровать по req.categories
        products = await self.product_repo.list_all()

        predictions: List[ProductPrediction] = []

        # ограничим количество товаров чтобы не заваливать фронт
        for p in products[:10]:
            # грубая эвристика прогноза
            # ожидаем что за период уйдёт какая-то доля от оптимального стока
            base_demand = (p.optimal_stock or 100) / max(req.period_days, 1) * 0.5

            predictions.append(
                ProductPrediction(
                    product_id=p.id,
                    category=p.category,
                    expected_demand=int(base_demand),
                    expected_stockout_in_days=None,  # можно рассчитать позже
                )
            )

        # Уровень уверенности модели — пока просто рандом от 0.7 до 0.95
        confidence_fake = uniform(0.7, 0.95)

        return AIPredictionResponse(
            predictions=predictions,
            confidence=round(confidence_fake, 2),
        )
