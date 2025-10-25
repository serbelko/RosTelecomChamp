from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.db.base import InventoryHistory
from app.repo.robot import RobotRepository

class RobotService:
    def __init__(self, robot_repo: RobotRepository):
        self.repo = robot_repo

    async def process_robot_data(self, payload: dict):
        """
        Обработка данных, присланных роботом.
        """
        robot_id = payload["robot_id"]
        battery = payload["battery_level"]
        zone = payload["zone"]
        row_number = payload["row_number"]
        shelf_number = payload["shelf_number"]
        try:
        # 1. Создаём или обновляем робота
            robot = await self.repo.create_or_update(
                robot_id=robot_id,
                battery_level=battery,
                zone=zone,
                row_number=row_number,
                shelf_number=shelf_number,
            )

        except Exception as e:
            raise ValueError("Failed to create or update robot", e)

        # 2. Добавляем записи о сканировании товаров
        for item in payload.get("scanned_products", []):
            history = InventoryHistory(
                robot_id=robot.id,
                product_id=item["product_id"],
                quantity=item["quantity"],
                zone=zone,
                row_number=row_number,
                shelf_number=shelf_number,
                status="OK",
                scanned_at=datetime.utcnow(),
            )
        try:
            self.db.add(history)
        except Exception as e:
            raise ValueError("Failed to add inventory history", e)

        await self.db.commit()
