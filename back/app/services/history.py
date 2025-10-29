# app/services/history_service.py

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Sequence, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.repo.inventory import InventoryHistoryRepository
from app.schemas.inventory import (
    InventoryRecordCreate,
    InventoryRecordOut,
    InventoryHistoryListOut,
    InventorySummaryOut,
    InventoryActivityOut,
    InventoryActivityPoint,
)


class HistoryService:
    """
    Сервисный слой над InventoryHistoryRepository.

    Задачи:
    - валидация входных данных (уже делает Pydantic)
    - вызов репозитория
    - commit/refresh при изменениях
    - преобразование ORM -> Pydantic для ответа наружу
    """

    def __init__(self, repo: InventoryHistoryRepository):
        self.repo = repo

    # ---------------------------
    # CREATE
    # ---------------------------

    async def create_record(
        self,
        rec: InventoryRecordCreate,
    ) -> InventoryRecordOut:
        """
        Создать одну запись инвентаризации (одна строка сканирования).
        Используется, например, при приёме данных от робота или при ручной загрузке.
        """
        obj = await self.repo.create_one(rec)

        # коммитим транзакцию на уровне сервиса
        await self.repo.session.commit()
        # обновим объект из БД, чтобы были id / created_at
        await self.repo.session.refresh(obj)

        return InventoryRecordOut.model_validate(obj)

    async def create_batch(
        self,
        records: List[InventoryRecordCreate],
    ) -> List[InventoryRecordOut]:
        """
        Массовая вставка нескольких строк инвентаризации.
        Например: CSV импорт или робот прислал пачку scan_results.
        """
        objs = await self.repo.create_many(records)

        await self.repo.session.commit()

        # refresh для всех, чтобы гарантированно получить id/created_at
        for o in objs:
            await self.repo.session.refresh(o)

        return [InventoryRecordOut.model_validate(o) for o in objs]

    # ---------------------------
    # READ / HISTORY
    # ---------------------------

    async def get_history(
        self,
        *,
        dt_from: Optional[datetime],
        dt_to: Optional[datetime],
        zones: Optional[Sequence[str]],
        statuses: Optional[Sequence[str]],
        product_id: Optional[str],
        q: Optional[str],
        limit: int,
        offset: int,
        sort_by: str = "scanned_at",
        sort_dir: str = "desc",
    ) -> InventoryHistoryListOut:
        """
        Исторические данные с фильтрами, пагинацией и сортировкой.
        То, что нужно для экрана /history.
        """
        items_orm, total = await self.repo.list(
            dt_from=dt_from,
            dt_to=dt_to,
            zones=zones,
            statuses=statuses,
            product_id=product_id,
            q=q,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

        items = [InventoryRecordOut.model_validate(obj) for obj in items_orm]

        return InventoryHistoryListOut(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_recent_scans(
        self,
        *,
        limit: int = 20,
    ) -> List[InventoryRecordOut]:
        """
        Последние N сканов (для таблицы 'последние сканирования' на дашборде).
        """
        objs = await self.repo.recent_scans(limit=limit)
        return [InventoryRecordOut.model_validate(o) for o in objs]

    async def get_records_by_ids(
        self,
        ids: Sequence[int],
    ) -> List[InventoryRecordOut]:
        """
        Достаём конкретные строки по ID.
        Это удобно для экспорта Excel/PDF: фронт прислал массив выбранных ID.
        """
        objs = await self.repo.get_by_ids(ids)
        return [InventoryRecordOut.model_validate(o) for o in objs]

    # ---------------------------
    # SUMMARY / KPI
    # ---------------------------

    async def get_summary(
        self,
        *,
        dt_from: Optional[datetime],
        dt_to: Optional[datetime],
        zones: Optional[Sequence[str]],
        statuses: Optional[Sequence[str]],
        product_id: Optional[str],
    ) -> InventorySummaryOut:
        """
        Сводная статистика под текущим фильтром:
        total, unique_products, OK/LOW_STOCK/CRITICAL.
        Это данные для KPI-блока на странице истории.
        """
        raw = await self.repo.summary(
            dt_from=dt_from,
            dt_to=dt_to,
            zones=zones,
            statuses=statuses,
            product_id=product_id,
        )
        # repo.summary возвращает dict[str, int], нам нужно InventorySummaryOut
        return InventorySummaryOut.model_validate(raw)

    # ---------------------------
    # ACTIVITY / GRAPH
    # ---------------------------

    async def get_activity_last_hour(
        self,
    ) -> InventoryActivityOut:
        """
        Активность за последний час (по минутам),
        для графика активности роботов.
        """
        raw_points = await self.repo.activity_last_hour()
        # raw_points — это List[Tuple[datetime, int]]

        points = [
            InventoryActivityPoint(
                timestamp_minute=ts,
                count=cnt,
            )
            for (ts, cnt) in raw_points
        ]

        return InventoryActivityOut(points=points)

    # ---------------------------
    # DELETE
    # ---------------------------

    async def delete_records(
        self,
        ids: Sequence[int],
    ) -> int:
        """
        Удаляет записи по ID.
        Возвращает, сколько реально удалено.
        После удаления делает commit.
        """
        deleted_count = await self.repo.delete_by_ids(ids)
        await self.repo.session.commit()
        return deleted_count
