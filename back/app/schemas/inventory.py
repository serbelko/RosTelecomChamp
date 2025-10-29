# app/schemas/inventory.py

from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


#
# Базовая запись инвентаризации (общие поля)
#
class InventoryRecordBase(BaseModel):
    robot_id: Optional[str] = Field(
        None,
        description="ID робота, который сделал скан"
    )
    product_id: str = Field(
        ...,
        description="Артикул товара (FK на products.id)"
    )
    quantity: int = Field(
        ...,
        ge=0,
        description="Фактическое количество на полке"
    )
    zone: str = Field(
        ...,
        description="Зона склада (A/B/C/..)"
    )
    row_number: Optional[int] = Field(
        None,
        description="Ряд внутри зоны"
    )
    shelf_number: Optional[int] = Field(
        None,
        description="Полка внутри ряда"
    )
    status: Optional[Literal["OK", "LOW_STOCK", "CRITICAL"]] = Field(
        None,
        description="Состояние остатка, если рассчитано"
    )
    scanned_at: datetime = Field(
        ...,
        description="Когда это было отсканировано роботом"
    )


#
# То, что приходит снаружи (от робота / из CSV / из ручного импорта)
#
class InventoryRecordCreate(InventoryRecordBase):
    """
    Используется для записи новой строки инвентаризации.
    """


#
# Ответ наружу по одной строке истории
#
class InventoryRecordOut(InventoryRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="PK строки в inventory_history")
    created_at: datetime = Field(
        ...,
        description="Когда запись была сохранена системой"
    )


#
# Пагинированный ответ для /api/inventory/history
#
class InventoryHistoryListOut(BaseModel):
    items: List[InventoryRecordOut]
    total: int
    limit: int
    offset: int


#
# Сводка по фильтрам (используется на экране History для KPI)
#
class InventorySummaryOut(BaseModel):
    total: int = Field(..., description="Всего записей по текущему фильтру")
    unique_products: int = Field(..., description="Сколько уникальных product_id")
    OK: int
    LOW_STOCK: int
    CRITICAL: int


#
# Точка активности (для графика активности роботов за последний час)
#
class InventoryActivityPoint(BaseModel):
    timestamp_minute: datetime = Field(
        ...,
        description="Метка времени, округленная до минуты"
    )
    count: int = Field(
        ...,
        description="Сколько сканов было в эту минуту"
    )


class InventoryActivityOut(BaseModel):
    points: List[InventoryActivityPoint]


#
# Батч на импорт
#
class InventoryBatchCreateIn(BaseModel):
    """
    Для массовой вставки нескольких строк
    (например: CSV загрузка или робот прислал пачку сканов).
    """
    records: List[InventoryRecordCreate]


class PaginationOut(BaseModel):
    limit: int
    offset: int


class InventoryHistoryResponse(BaseModel):
    total: int
    items: List[InventoryRecordOut]
    pagination: PaginationOut