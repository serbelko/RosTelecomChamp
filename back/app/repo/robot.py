from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Tuple

import structlog
from app.db.base import Robots
from app.schemas.robot import RobotBase

logger = structlog.get_logger(__name__)


class RobotRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, robot_id: str) -> Optional[Robots]:
        """Загрузить робота по robot_id (или None, если не найден)."""
        stmt = select(Robots).where(Robots.robot_id == robot_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def create(self, robot_data: RobotBase) -> Robots:
        """Создать НОВОГО робота (без коммита)."""
        robot = Robots(
            robot_id=robot_data.robot_id,
            status=robot_data.status or "online",
            battery_level=robot_data.battery_level,
            last_update=robot_data.last_update,
            zone=robot_data.location.zone,
            row=robot_data.location.row,
            shelf=robot_data.location.shelf,
        )
        self.db.add(robot)
        logger.info(
            "robot.created_staged",
            robot_id=robot.robot_id,
            status=robot.status,
            battery=robot.battery_level,
            zone=robot.zone,
            row=robot.row,
            shelf=robot.shelf,
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
            zone=robot.zone,
            row=robot.row,
            shelf=robot.shelf,
        )
        return robot

    async def upsert_robot(self, robot_data: RobotBase) -> Tuple[Robots, bool]:
        """
        Универсальная операция: создает или обновляет.
        Возвращает (робот, created_flag).
        Без коммита — управление транзакцией на вызывающей стороне.
        """
        robot = await self.get_by_id(robot_data.robot_id)

        created = False
        if robot is None:
            robot = await self.create(robot_data)
            created = True
        else:
            robot = await self.update(robot, robot_data)

        return robot, created
