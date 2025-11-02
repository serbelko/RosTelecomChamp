# app/repo/robot.py
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.base import Robots
from app.schemas.robot import RobotBase

logger = structlog.get_logger(__name__)


class RobotRepository:
    """Репозиторий для таблицы robots. НИКАКИХ commit() внутри — только staged-операции + flush()."""

    def __init__(self, session: AsyncSession):
        # ВАЖНО: единое имя поля — session (НЕ db)
        self.session = session

    async def get_by_id(self, robot_id: str) -> Optional[Robots]:
        """Загрузить робота по robot_id (или None, если не найден)."""
        stmt = select(Robots).where(Robots.robot_id == robot_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create(self, robot_data: RobotBase) -> Robots:
        """Создать нового робота (без коммита)."""
        robot = Robots(
            robot_id=robot_data.robot_id,
            status=robot_data.status or "online",
            battery_level=robot_data.battery_level,
            last_update=robot_data.last_update,
            zone=robot_data.location.zone,
            row=robot_data.location.row,
            shelf=robot_data.location.shelf,
        )
        self.session.add(robot)
        logger.info(
            "robot.created_staged",
            robot_id=robot.robot_id,
            status=robot.status,
            battery=robot.battery_level,
            zone=robot.zone, row=robot.row, shelf=robot.shelf,
        )
        return robot

    async def update(self, robot: Robots, robot_data: RobotBase) -> Robots:
        """Обновить существующего робота (без коммита)."""
        robot.status = robot_data.status or robot.status
        robot.battery_level = robot_data.battery_level
        robot.last_update = robot_data.last_update
        robot.zone = robot_data.location.zone
        robot.row = robot_data.location.row
        robot.shelf = robot_data.location.shelf

        logger.info(
            "robot.updated_staged",
            robot_id=robot.robot_id,
            status=robot.status,
            battery=robot.battery_level,
            zone=robot.zone, row=robot.row, shelf=robot.shelf,
        )
        return robot

    async def upsert_robot(self, robot_data: RobotBase) -> Tuple[Robots, bool]:
        """
        Создать или обновить робота (без коммита).
        Возвращает (robot, created_flag).
        """
        robot = await self.get_by_id(robot_data.robot_id)
        created = False
        if robot is None:
            robot = await self.create(robot_data)
            created = True
        else:
            robot = await self.update(robot, robot_data)
        # flush выполняет вызывающая сторона (сервис), чтобы гарантировать видимость FK
        return robot, created

    async def get_all(
        self,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Вернуть компактный список роботов:
        [{"robot_id": "...", "status": "...", "battery_level": 87}, ...]
        """
        stmt = (
            select(Robots.robot_id, Robots.status, Robots.battery_level)
            .order_by(Robots.robot_id)
            .offset(offset)
        )
        if limit is not None:
            stmt = stmt.limit(limit)

        rows = (await self.session.execute(stmt)).mappings().all()
        return [
            {
                "robot_id": row["robot_id"],
                "status": row["status"],
                "battery_level": row["battery_level"],
            }
            for row in rows
        ]
