from bson import ObjectId
from sqlalchemy import select
from app.db.base import Base, Robots
from app.schemas.robot import RobotCreate, RobotUpdate
from typing import Optional
from datetime import datetime
import structlog    

logger = structlog.get_logger(__name__)


class RobotRepository:
    def __init__(self, db: Base):
        self.db = db

    async def create_robot(self, payload: RobotCreate) -> Robots:
        robot = Robots(
            id=payload.id,
            status=payload.status,
            battery_level=payload.battery_level,
            current_zone=payload.current_zone,
            current_row=payload.current_row,
            current_shelf=payload.current_shelf,
        )
        self.db.add(robot)
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.info("Robot create conflict", id=payload.id)
            raise ValueError("Robot with this ID already exists", e) from e

        await self.db.refresh(robot)
        logger.info("Robot created", robot_id=str(robot.id))
        return robot
    
    async def update_robot(self, payload: RobotUpdate) -> Optional[Robots]:
        query = select(Robots).where(Robots.id == payload.id)
        result = await self.db.execute(query)
        robot = result.scalars().first()

        if not robot:
            logger.info("Robot not found for update", id=payload.id)
            return None

        robot.status = payload.status
        robot.battery_level = payload.battery_level
        robot.last_update = datetime.fromisoformat(payload.last_update)
        robot.current_zone = payload.current_zone
        robot.current_row = payload.current_row
        robot.current_shelf = payload.current_shelf

        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.info("Robot update conflict", id=payload.id)
            raise ValueError("Robot with this ID already exists", e) from e

        await self.db.refresh(robot)
        logger.info("Robot updated", robot_id=str(robot.id))
        return robot