# app/services/dashboard.py
from __future__ import annotations
from typing import List
from datetime import datetime, timedelta

from sqlalchemy import select, func, desc

from app.db.base import Robots, InventoryHistory
from app.repo.robot import RobotRepository
from app.repo.inventory import InventoryHistoryRepository
from app.schemas.dashboard import (
    RobotInfo,
    RecentScanItem,
    DashboardStatistics,
    DashboardResponse,
)


class DashboardService:
    def __init__(
        self,
        robot_repo: RobotRepository,
        history_repo: InventoryHistoryRepository,
    ):
        self.robot_repo = robot_repo
        self.history_repo = history_repo

    async def get_dashboard_data(self) -> DashboardResponse:
        """
        Собирает:
        - текущее состояние роботов
        - последние сканы
        - статистику по складу
        """

        # 1. Список роботов
        robots = await self._get_all_robots()

        # 2. Последние сканы (например, последние 20 записей)
        recent_scans = await self._get_recent_scans(limit=20)

        # 3. Статистика
        stats = await self._get_statistics()

        return DashboardResponse(
            robots=robots,
            recent_scans=recent_scans,
            statistics=stats,
        )

    async def _get_all_robots(self) -> List[RobotInfo]:
        """
        Берём всех роботов.
        """
        session = self.robot_repo.session  # AsyncSession
        query = select(Robots)
        result = await session.execute(query)
        rows = result.scalars().all()

        return [
            RobotInfo(
                robot_id=row.robot_id,
                status=row.status,
                battery_level=row.battery_level,
                last_update=row.last_update,
                zone=row.zone,
                row=row.row,
                shelf=row.shelf,
            )
            for row in rows
        ]

    async def _get_recent_scans(self, limit: int = 20) -> List[RecentScanItem]:
        """
        Достаём последние N записей из инвентарной истории.
        """
        session = self.history_repo.session  # AsyncSession
        query = (
            select(InventoryHistory)
            .order_by(desc(InventoryHistory.scanned_at))
            .limit(limit)
        )
        result = await session.execute(query)
        rows = result.scalars().all()

        return [
            RecentScanItem(
                id=row.id,
                robot_id=row.robot_id,
                product_id=row.product_id,
                quantity=row.quantity,
                status=row.status,
                zone=row.zone,
                row_number=row.row_number,
                shelf_number=row.shelf_number,
                scanned_at=row.scanned_at,
            )
            for row in rows
        ]

    async def _get_statistics(self) -> DashboardStatistics:
        """
       Собираем агрегированную информацию:
        - всего роботов
        - offline роботов
        - количество CRITICAL/LOW_STOCK ситуаций
        - сколько сканов сделано за последний час
        """

        session_r = self.robot_repo.session
        session_h = self.history_repo.session

        # всего роботов
        q_total = select(func.count(Robots.robot_id))
        total_robots = (await session_r.execute(q_total)).scalar_one() or 0

        # оффлайн роботов
        q_offline = select(func.count(Robots.robot_id)).where(Robots.status == "offline")
        offline_robots = (await session_r.execute(q_offline)).scalar_one() or 0

        # критичные остатки
        q_crit = select(func.count(InventoryHistory.id)).where(
            InventoryHistory.status.in_(["CRITICAL", "CRIT"])
        )
        critical_items = (await session_h.execute(q_crit)).scalar_one() or 0

        # низкие остатки
        q_low = select(func.count(InventoryHistory.id)).where(
            InventoryHistory.status.in_(["LOW_STOCK", "LOW"])
        )
        low_stock_items = (await session_h.execute(q_low)).scalar_one() or 0

        # сканов за последний час
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        q_last_hour = select(func.count(InventoryHistory.id)).where(
            InventoryHistory.scanned_at >= one_hour_ago
        )
        scans_last_hour = (await session_h.execute(q_last_hour)).scalar_one() or 0

        return DashboardStatistics(
            total_robots=total_robots,
            offline_robots=offline_robots,
            critical_items=critical_items,
            low_stock_items=low_stock_items,
            scans_last_hour=scans_last_hour,
        )
