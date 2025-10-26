from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.db.base import InventoryHistory
from app.repo.robot import RobotRepository
from app.schemas.robot import RobotBase

class RobotService:
    def __init__(self, robot_repo: RobotRepository):
        self.repo = robot_repo

    async def process_robot_data(self, robot: RobotBase):
        """
        Обработка данных, присланных роботом.
        """
        try:
        # 1. Создаём или обновляем робота
            robot = await self.repo.create_or_update_robot(robot)

        except Exception as e:
            raise ValueError("Failed to create or update robot", e)

        # 2. Добавляем записи о сканировании товаров
        # for item in robot.get("scanned_products", []):
        #     history = InventoryHistory(  
        #         robot_id=robot.robot_id,
        #         product_id=item["product_id"],
        #         quantity=item["quantity"],
        #         zone=zone,
        #         row_number=row_number,
        #         shelf_number=shelf_number,
        #         status="OK",
        #         scanned_at=datetime.now(),
        #     )
        # try:
        #     self.db.add(history)
        # except Exception as e:
        #     raise ValueError("Failed to add inventory history", e)

        # await self.db.commit()

    async def get_robot_status(self, robot_id: str) -> dict:
        """
        Получение статуса робота по его ID.
        """
        robot = await self.repo.get_by_id(robot_id)
        if not robot:
            raise ValueError("Robot not found")

        return {
            "robot_id": robot.robot_id,
            "status": robot.status,
            "battery_level": robot.battery_level,
            "last_update": robot.last_update.isoformat(),
            "current_zone": robot.current_zone,
            "current_row": robot.current_row,
            "current_shelf": robot.current_shelf,
        }