from bson import ObjectId
from sqlalchemy import select
from app.db.base import Base, Robots
from app.schemas.robot import RobotBase, RobotOut
from typing import Optional
from datetime import datetime
import structlog    
from pydantic import ValidationError
from fastapi.encoders import jsonable_encoder

logger = structlog.get_logger(__name__)


class RobotRepository:
    def __init__(self, db: Base):
        self.db = db

    
    async def create_or_update_robot(self, robot_data: RobotBase) -> RobotOut:

        query = select(Robots).where(Robots.robot_id == robot_data.robot_id)
        result = await self.db.execute(query)
        robot = result.scalars().first()

        if not robot:
            logger.info("Robot not found for update", id=robot_data.robot_id)
            robot = Robots(
                robot_id=robot_data.robot_id,
                battery_level=robot_data.battery_level,
                zone=robot_data.location.zone,
                row=robot_data.location.row,
                shelf=robot_data.location.shelf,
                last_update=robot_data.last_update
            )
            self.db.add(robot)
        else:
            robot.battery_level = robot_data.battery_level
            robot.last_update = robot_data.last_update
            robot.zone = robot_data.location.zone
            robot.row = robot_data.location.row
            robot.shelf = robot_data.location.shelf
        try:
            await self.db.commit()
            await self.db.refresh(robot)
            logger.info("Robot updated", robot_id=str(robot.robot_id))
            return RobotOut.model_validate(robot)
        except Exception as e:
            await self.db.rollback()
            logger.info("Robot create or update conflict", id=robot_data.robot_id)
            raise
        
