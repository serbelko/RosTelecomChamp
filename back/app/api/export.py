from __future__ import annotations

from typing import List
from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import StreamingResponse
from dependency_injector.wiring import inject, Provide
from io import BytesIO

from app.core.container import Container
from app.services.export_service import ExportService

router = APIRouter(
    prefix="/api/export",
    tags=["export"],
)

@router.get("/excel")
@inject
async def export_excel(
    ids: str = Query(..., description="Comma-separated list of inventory_history IDs"),
    svc: ExportService = Depends(Provide[Container.export_service]),
):
    """
    Пример запроса:
    GET /api/export/excel?ids=1,2,3
    """

    # Разбираем ids=1,2,3 в [1,2,3]
    try:
        id_list: List[int] = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid 'ids' format. Use ?ids=1,2,3")

    if not id_list:
        raise HTTPException(status_code=400, detail="No valid IDs provided")

    # генерируем Excel
    excel_bytes = await svc.export_inventory_history_to_excel(id_list)

    # готовим StreamingResponse
    filename = "inventory_export.xlsx"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }

    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
