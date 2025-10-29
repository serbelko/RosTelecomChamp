# app/api/import_csv.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.services.import_inventory import InventoryImportService
from app.schemas.import_inventory import ImportResultResponse

router = APIRouter(
    prefix="/api/inventory",
    tags=["inventory-import"],
)

@router.post("/import", response_model=ImportResultResponse)
@inject
async def import_inventory(
    file: UploadFile = File(...),
    svc: InventoryImportService = Depends(Provide[Container.inventory_import_service]),
):
    if file.content_type not in [
        "text/csv",
        "application/vnd.ms-excel",
        "application/octet-stream",  # на всякий случай
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. CSV required.",
        )

    contents = await file.read()
    csv_text = contents.decode("utf-8", errors="replace")

    # Важно: здесь вызываем именно import_csv()
    result = await svc.import_csv(csv_text)

    # result - это InventoryImportResult, но у нас response_model=ImportResultResponse
    # Убедимся, что они совпадают по полям. Если да — можно просто return result.
    return result
