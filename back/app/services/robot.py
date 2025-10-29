# app/services/robot.py

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from app.repo.robot import RobotRepository
from app.repo.inventory import InventoryHistoryRepository
from app.repo.product import ProductRepository
from app.schemas.robot import RobotBase
from app.schemas.inventory import InventoryRecordCreate
from app.ws.notifier import notify_robot_update, notify_inventory_alert


class RobotService:
    def __init__(
        self,
        robot_repo: RobotRepository,
        product_repo: ProductRepository,
        history_repo: InventoryHistoryRepository,
    ):
        self.robot_repo = robot_repo
        self.product_repo = product_repo
        self.history_repo = history_repo

    async def process_robot_data(self, robot: RobotBase) -> Dict[str, Any]:
        """
        Поток:
        1. upsert робота
        2. ensure products
        3. save inventory_history
        4. WS нотификации
        """

        # --- 1. апдейт/создание робота ---
        robot_db = await self.robot_repo.create_or_update_robot(robot)
        # внутри репозитория робот коммитится (у тебя так уже сделано)
        # это окей

        # --- 2. гарантируем наличие товаров в products ---
        # соберём {product_id: product_name} из scan_results
        products_map: Dict[str, str] = {}
        for scan in robot.scan_results:
            # если нет имени — хотя бы id будет name
            products_map[scan.product_id] = scan.product_name or scan.product_id

        # добавим недостающие SKU в таблицу products
        await self.product_repo.ensure_products_exist(products_map)
        # важно: зафиксируем это в базе ДО того, как писать историю,
        # иначе FK на inventory_history снова упадёт
        await self.product_repo.session.commit()

        # --- 3. пишем инвентаризацию в history ---
        zone = robot.location.zone
        row_number = robot.location.row
        shelf_number = robot.location.shelf
        scanned_at_ts = robot.last_update or datetime.utcnow()

        records_to_create: List[InventoryRecordCreate] = []

        for item in robot.scan_results:
            status_norm = item.status.upper() if item.status else None

            rec = InventoryRecordCreate(
                robot_id=robot.robot_id,
                product_id=item.product_id,
                quantity=item.quantity,
                zone=zone,
                row_number=row_number,
                shelf_number=shelf_number,
                status=status_norm,
                scanned_at=scanned_at_ts,
            )
            records_to_create.append(rec)

        if records_to_create:
            await self.history_repo.create_many(records_to_create)
            await self.history_repo.session.commit()

        # --- 4. WebSocket обновления в UI ---
        await notify_robot_update({
            "robot_id": robot.robot_id,
            "battery_level": robot.battery_level,
            "zone": zone,
            "row": row_number,
            "shelf": shelf_number,
            "last_update": robot.last_update.isoformat(),
        })

        critical_ids = [
            scan.product_id
            for scan in robot.scan_results
            if scan.status and scan.status.upper() in ("CRITICAL", "CRIT")
        ]

        low_ids = [
            scan.product_id
            for scan in robot.scan_results
            if scan.status and scan.status.upper() in ("LOW_STOCK", "LOW")
        ]

        now = datetime.utcnow()

        if critical_ids:
            await notify_inventory_alert(
                zone=zone,
                product_ids=critical_ids,
                severity="CRITICAL",
                at=now,
            )

        if low_ids:
            await notify_inventory_alert(
                zone=zone,
                product_ids=low_ids,
                severity="LOW",
                at=now,
            )

        return {
            "robot": {
                "robot_id": robot_db.robot_id,
                "battery_level": robot.battery_level,
                "zone": zone,
                "row": row_number,
                "shelf": shelf_number,
                "last_update": robot.last_update.isoformat(),
            },
            "ingested_records": len(records_to_create),
        }
