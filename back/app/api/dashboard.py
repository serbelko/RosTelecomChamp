# app/api/dashboard.py
from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide

from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import DashboardService
from app.core.container import Container  # контейнер DI

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/current", response_model=DashboardResponse)
@inject
async def get_dashboard_current(
    svc: DashboardService = Depends(Provide[Container.dashboard_service]),
):
    """
    Получение текущего состояния склада.

    Возвращает:
    {
      "robots": [...],
      "recent_scans": [...],
      "statistics": {...}
    }
    """
    return await svc.get_dashboard_data()
