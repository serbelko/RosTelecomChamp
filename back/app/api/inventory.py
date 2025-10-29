from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.services.history import HistoryService
from app.schemas.inventory import (
    InventoryHistoryResponse,
    PaginationOut,
    
)

router = APIRouter(
    prefix="/api/inventory",
    tags=["inventory"],
)


@router.get("/history", response_model=InventoryHistoryResponse)
@inject
async def get_history(
    # фильтры периода и выборок
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = Query(None, alias="to"),
    zone: Optional[str] = Query(None),
    status: Optional[str] = Query(None),

    # разруливаем пагинацию и сортировку
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("scanned_at"),
    sort_dir: str = Query("desc"),

    svc: HistoryService = Depends(Provide[Container.history_service]),
):
    """
    Исторические данные
    GET /api/inventory/history?from=...&to=...&zone=A&status=critical

    Возвращает:
    {
      "total": number,
      "items": [...],
      "pagination": { "limit": x, "offset": y }
    }
    """

    # адаптация query-параметров к сигнатуре сервиса HistoryService.get_history
    zones = [zone] if zone else None
    statuses = [status.upper()] if status else None  # "critical" -> "CRITICAL"
                                                    # можно убрать .upper(), если фронт шлёт уже нормализованно

    service_result = await svc.get_history(
        dt_from=from_,
        dt_to=to,
        zones=zones,
        statuses=statuses,
        product_id=None,  # тут можно потом добавить ?product_id=... если нужно
        q=None,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


    response = InventoryHistoryResponse(
        total=service_result.total,
        items=service_result.items,
        pagination=PaginationOut(
            limit=service_result.limit,
            offset=service_result.offset,
        ),
    )
    return response

