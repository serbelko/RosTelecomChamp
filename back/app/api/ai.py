from fastapi import APIRouter, Depends, HTTPException
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.schemas.ai import AIPredictionRequest, AIPredictionResponse
from app.services.ai import AIService

router = APIRouter(
    prefix="/api/ai",
    tags=["ai"],
)

@router.post("/predict", response_model=AIPredictionResponse)
@inject
async def predict_demand(
    body: AIPredictionRequest,
    svc: AIService = Depends(Provide[Container.ai_service]),
):
    """
    Прогноз спроса по складу.
    """
    try:
        result = await svc.predict(body)
        return result
    except Exception as e:
        # можно по-умному логировать здесь
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")
