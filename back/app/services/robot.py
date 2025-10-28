from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict
from datetime import datetime
from app.db.base import InventoryHistory
from app.repo.robot import RobotRepository
from app.schemas.robot import RobotBase
from app.ws.notifier import notify_robot_update, notify_inventory_alert

def _safe_get(obj: Any, name: str, default=None):
    if obj is None:
        return default
    # pydantic/BaseModel или произвольный объект
    if hasattr(obj, name):
        return getattr(obj, name)
    # dict
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default


class RobotService:
    def __init__(self, robot_repo: RobotRepository):
        self.repo = robot_repo

    
    async def process_robot_data(self, robot: RobotBase):
        """
        Обработка данных от робота без использования поля status (его нет в RobotBase).
        """

        # --- [БД] при необходимости создайте/обновите запись о роботе ---
        # robot_db = await self.repo.create_or_update_robot(robot)  # если нужно

        # --- [WS] Нотификации ---
        # Формируем компактный payload без status
        ws_payload: Dict[str, Any] = {
            "robot_id": _safe_get(robot, "robot_id"),
            "battery_level": _safe_get(robot, "battery_level"),
            "current_zone": _safe_get(robot, "current_zone"),
            "current_row": _safe_get(robot, "current_row"),
            "current_shelf": _safe_get(robot, "current_shelf"),
            "last_update": datetime.utcnow().isoformat(),
        }
        # Убираем None, чтобы не засорять фронт
        ws_payload = {k: v for k, v in ws_payload.items() if v is not None}

        # Обновление карточки конкретного робота
        await notify_robot_update(robot)

        # Алерты по товарам (если приходят)
        scanned = (
            _safe_get(robot, "scanned_products")
            or _safe_get(robot, "scanned_items")
            or []
        )

        try:
            def g(o, n, d=None):  # короткий алиас
                return _safe_get(o, n, d)

            # Если в элементах нет status, фильтры будут пустыми, и мы просто ничего не отправим
            critical_ids = [g(it, "product_id") for it in scanned
                            if g(it, "product_id") is not None and g(it, "status") in ("CRITICAL", "CRIT")]
            low_ids = [g(it, "product_id") for it in scanned
                    if g(it, "product_id") is not None and g(it, "status") in ("LOW_STOCK", "LOW")]

            zone = _safe_get(robot, "current_zone") or (g(scanned[0], "zone") if scanned else None)
            now = datetime.utcnow()

            if critical_ids:
                await notify_inventory_alert(
                    zone=zone or "UNKNOWN",
                    product_ids=critical_ids,
                    severity="CRITICAL",
                    at=now,
                )
            if low_ids:
                await notify_inventory_alert(
                    zone=zone or "UNKNOWN",
                    product_ids=low_ids,
                    severity="LOW",
                    at=now,
                )
        except Exception:
            # нотификации не должны ломать ingestion-пайплайн
            pass


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
