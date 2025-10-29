from pydantic import BaseModel
from typing import List
from datetime import datetime

class InventoryImportRow(BaseModel):
    robot_id: str
    product_id: str
    quantity: int
    zone: str
    row: int
    shelf: int
    status: str
    scanned_at: datetime

class InventoryImportResult(BaseModel):
    success: int
    failed: int
    errors: List[str]  # список строк с описаниями ошибок

class ImportResultResponse(BaseModel):
    success: int
    failed: int
    errors: List[str]  # <-- ВАЖНО! то же самое
