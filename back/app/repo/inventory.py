# app/repositories/inventory_history.py

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy import (
    and_,
    asc,
    desc,
    func,
    or_,
    select,
    delete,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import InventoryHistory
from app.schemas.inventory import InventoryRecordCreate


SortField = str   # допустимые поля сортировки
SortDir = str     # "asc" | "desc"


class InventoryHistoryRepository:
    """
    Репозиторий для работы с таблицей inventory_history (асинхронный).
    Никаких commit() внутри — коммит делает сервис после удачной операции.
    """

    _SORT_FIELDS = {
        "scanned_at": InventoryHistory.scanned_at,
        "product_id": InventoryHistory.product_id,
        "zone": InventoryHistory.zone,
        "status": InventoryHistory.status,
        "quantity": InventoryHistory.quantity,
        "row_number": InventoryHistory.row_number,
        "shelf_number": InventoryHistory.shelf_number,
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------
    # Внутреннее: построить базовый select с фильтрами
    # ------------------------------------------------------------------

    def _filtered_base_query(
        self,
        *,
        dt_from: Optional[datetime],
        dt_to: Optional[datetime],
        zones: Optional[Sequence[str]],
        statuses: Optional[Sequence[str]],
        product_id: Optional[str],
        q: Optional[str],
    ):
        conds = []

        if dt_from:
            conds.append(InventoryHistory.scanned_at >= dt_from)
        if dt_to:
            conds.append(InventoryHistory.scanned_at <= dt_to)
        if zones:
            conds.append(InventoryHistory.zone.in_(zones))
        if statuses:
            conds.append(InventoryHistory.status.in_(statuses))
        if product_id:
            conds.append(InventoryHistory.product_id == product_id)
        if q:
            pattern = f"%{q.strip()}%"
            conds.append(
                or_(
                    InventoryHistory.product_id.ilike(pattern),
                    InventoryHistory.zone.ilike(pattern),
                    InventoryHistory.status.ilike(pattern),
                )
            )

        stmt = select(InventoryHistory)
        if conds:
            stmt = stmt.where(and_(*conds))
        return stmt

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def create_one(
        self,
        rec: InventoryRecordCreate,
    ) -> InventoryHistory:
        """
        Создать одну запись инвентаризации.
        Возвращает ORM-объект после flush().
        """
        obj = InventoryHistory(
            robot_id=rec.robot_id,
            product_id=rec.product_id,
            quantity=rec.quantity,
            zone=rec.zone,
            row_number=rec.row_number,
            shelf_number=rec.shelf_number,
            status=rec.status,
            scanned_at=rec.scanned_at,
        )
        self.session.add(obj)
        await self.session.flush()  # после flush obj.id уже есть
        return obj

    async def create_many(
        self,
        records: List[InventoryRecordCreate],
    ) -> List[InventoryHistory]:
        """
        Массовое добавление нескольких строк.
        Возвращает список ORM-объектов.
        """
        objs: List[InventoryHistory] = []
        for rec in records:
            obj = InventoryHistory(
                robot_id=rec.robot_id,
                product_id=rec.product_id,
                quantity=rec.quantity,
                zone=rec.zone,
                row_number=rec.row_number,
                shelf_number=rec.shelf_number,
                status=rec.status,
                scanned_at=rec.scanned_at,
            )
            self.session.add(obj)
            objs.append(obj)

        await self.session.flush()
        return objs

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def recent_scans(
        self,
        *,
        limit: int = 20,
    ) -> List[InventoryHistory]:
        """
        Последние N записей по времени scanned_at (для блока 'последние сканирования').
        """
        stmt = (
            select(InventoryHistory)
            .order_by(InventoryHistory.scanned_at.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars())

    async def list(
        self,
        *,
        dt_from: Optional[datetime] = None,
        dt_to: Optional[datetime] = None,
        zones: Optional[Sequence[str]] = None,
        statuses: Optional[Sequence[str]] = None,
        product_id: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: SortField = "scanned_at",
        sort_dir: SortDir = "desc",
    ) -> Tuple[List[InventoryHistory], int]:
        """
        Основной список для /api/inventory/history:
        фильтры, поиск, сортировка, пагинация.
        Возвращает (items, total).
        """
        base_stmt = self._filtered_base_query(
            dt_from=dt_from,
            dt_to=dt_to,
            zones=zones,
            statuses=statuses,
            product_id=product_id,
            q=q,
        )

        # общее количество под текущим фильтром
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        # сортировка
        sort_col = self._SORT_FIELDS.get(sort_by, InventoryHistory.scanned_at)
        order_clause = asc(sort_col) if sort_dir.lower() == "asc" else desc(sort_col)

        # страница
        page_stmt = (
            base_stmt
            .order_by(order_clause)
            .limit(limit)
            .offset(offset)
        )

        page_res = await self.session.execute(page_stmt)
        items = list(page_res.scalars())

        return items, total

    async def get_by_ids(
        self,
        ids: Sequence[int],
    ) -> List[InventoryHistory]:
        """
        Получить конкретные строки по их id (для экспорта Excel/PDF).
        """
        if not ids:
            return []
        stmt = select(InventoryHistory).where(InventoryHistory.id.in_(ids))
        res = await self.session.execute(stmt)
        return list(res.scalars())

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    async def delete_by_ids(
        self,
        ids: Sequence[int],
    ) -> int:
        """
        Удалить строки истории (если политика разрешает).
        Возвращает количество удалённых записей.
        """
        if not ids:
            return 0
        stmt = delete(InventoryHistory).where(InventoryHistory.id.in_(ids))
        res = await self.session.execute(stmt)
        return res.rowcount or 0

    # ------------------------------------------------------------------
    # SUMMARY / KPI
    # ------------------------------------------------------------------

    async def summary(
        self,
        *,
        dt_from: Optional[datetime] = None,
        dt_to: Optional[datetime] = None,
        zones: Optional[Sequence[str]] = None,
        statuses: Optional[Sequence[str]] = None,
        product_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Возвращает агрегированную статистику по текущим фильтрам:
        total, unique_products и разбиение по статусам.
        """
        base_stmt = self._filtered_base_query(
            dt_from=dt_from,
            dt_to=dt_to,
            zones=zones,
            statuses=statuses,
            product_id=product_id,
            q=None,
        )

        # total
        total_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = (await self.session.execute(total_stmt)).scalar_one()

        # unique_products
        uniq_stmt = select(
            func.count(func.distinct(InventoryHistory.product_id))
        ).select_from(base_stmt.subquery())
        unique_products = (await self.session.execute(uniq_stmt)).scalar_one()

        # разбивка по статусам
        grouped_stmt = (
            select(
                InventoryHistory.status,
                func.count().label("cnt"),
            )
            .select_from(base_stmt.subquery())
            .group_by(InventoryHistory.status)
        )
        rows = (await self.session.execute(grouped_stmt)).all()
        by_status = {row[0] or "UNKNOWN": row[1] for row in rows}

        return {
            "total": total,
            "unique_products": unique_products,
            "OK": by_status.get("OK", 0),
            "LOW_STOCK": by_status.get("LOW_STOCK", 0),
            "CRITICAL": by_status.get("CRITICAL", 0),
        }

    # ------------------------------------------------------------------
    # ACTIVITY (для графика за последний час)
    # ------------------------------------------------------------------

    async def activity_last_hour(
        self,
        *,
        now: Optional[datetime] = None,
    ) -> List[Tuple[datetime, int]]:
        """
        Активность сканирования за последние 60 минут.
        Вернёт [(timestamp_minute, count), ...]
        timestamp_minute округлён до минут.
        """
        if now is None:
            now = datetime.utcnow()
        since = now - timedelta(hours=1)

        bucket = func.date_trunc("minute", InventoryHistory.scanned_at).label("bucket")

        stmt = (
            select(bucket, func.count().label("cnt"))
            .where(InventoryHistory.scanned_at >= since)
            .group_by(bucket)
            .order_by(bucket.asc())
        )

        res = await self.session.execute(stmt)
        return [(row.bucket, row.cnt) for row in res.all()]
    
    async def get_by_ids(self, ids: List[int]) -> List[InventoryHistory]:
        """Загружает записи истории инвентаря по списку ID."""
        if not ids:
            return []
        stmt = select(InventoryHistory).where(InventoryHistory.id.in_(ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
