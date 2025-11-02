# app/services/robot.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import structlog
from sqlalchemy.exc import SQLAlchemyError

from app.repo.robot import RobotRepository
# ВАЖНО: путь импорта должен совпадать с реальным местом файла!
# Если файл лежит в app/repositories/inventory_history.py, то импорт такой:
# from app.repositories.inventory_history import InventoryHistoryRepository
from app.repo.inventory import InventoryHistoryRepository
from app.repo.product import ProductRepository
from app.core.security import SecurityManager
from app.schemas.robot import (
    RobotBase, RobotRegisterRequest, RobotRegisterResponse, Location,
    RobotsListResponse, RobotForListOut
)
from app.schemas.inventory import InventoryRecordCreate
from app.ws.notifier import notify_robot_update, notify_inventory_alert

logger = structlog.get_logger(__name__)


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
        Транзакционно:
          1) upsert робота
          2) ensure products
          3) batch insert inventory_history
        Коммит/роллбек делает контекст session.begin().
        WS-ивенты отправляем после успешного коммита.
        """
        scanned_at_ts: datetime = robot.last_update or datetime.now(timezone.utc)
        zone = robot.location.zone
        row_number = robot.location.row
        shelf_number = robot.location.shelf
        scan_results = robot.scan_results or []

        logger.info(
            "robot.ingest_start",
            robot_id=robot.robot_id,
            zone=zone, row=row_number, shelf=shelf_number,
            battery=robot.battery_level, scans=len(scan_results),
        )

        inserted_records_count = 0

        # ЕДИНАЯ сессия для всех репозиториев
        session = self.history_repo.session
        self.product_repo.session = session
        self.robot_repo.session = session

        try:
            async with session.begin():
                # 1) upsert робота
                robot_db, created_flag = await self.robot_repo.upsert_robot(robot)
                # важно: сделать запись робота видимой для FK
                await session.flush()

                # 2) ensure products
                products_map: Dict[str, str] = {}
                for scan in scan_results:
                    if scan.product_id:
                        products_map[scan.product_id] = scan.product_name or scan.product_id

                if products_map:
                    await self.product_repo.ensure_products_exist(products_map)
                    await session.flush()

                # 3) batch insert history
                if scan_results:
                    records_to_create: List[InventoryRecordCreate] = []
                    for item in scan_results:
                        status_norm = item.status.upper() if item.status else None
                        records_to_create.append(
                            InventoryRecordCreate(
                                robot_id=robot_db.robot_id,  # используем фактическое значение из БД
                                product_id=item.product_id,
                                quantity=item.quantity,
                                zone=zone,
                                row_number=row_number,
                                shelf_number=shelf_number,
                                status=status_norm,
                                scanned_at=scanned_at_ts,
                            )
                        )
                    await self.history_repo.create_many(records_to_create)
                    inserted_records_count = len(records_to_create)

            # === ВНЕ транзакции: WS-события ===
            try:
                await notify_robot_update({
                    "robot_id": robot_db.robot_id,
                    "battery_level": robot.battery_level,
                    "zone": zone,
                    "row": row_number,
                    "shelf": shelf_number,
                    "status": robot_db.status or "active",
                    "last_update": (robot_db.last_update or scanned_at_ts).isoformat(),
                    "next_checkpoint": robot.next_checkpoint,
                })
            except Exception as e:
                logger.warning("ws.robot_update_failed", robot_id=robot.robot_id, error=str(e))

            critical_ids = [
                s.product_id for s in scan_results
                if s.status and s.status.upper() in ("CRITICAL", "CRIT")
            ]
            low_ids = [
                s.product_id for s in scan_results
                if s.status and s.status.upper() in ("LOW_STOCK", "LOW")
            ]
            now = datetime.now(timezone.utc)

            try:
                if critical_ids:
                    await notify_inventory_alert(
                        zone=zone, product_ids=critical_ids, severity="CRITICAL", at=now
                    )
                if low_ids:
                    await notify_inventory_alert(
                        zone=zone, product_ids=low_ids, severity="LOW", at=now
                    )
            except Exception as e:
                logger.warning(
                    "ws.alert_failed",
                    robot_id=robot.robot_id, critical_items=critical_ids, low_items=low_ids, error=str(e)
                )

            response = {
                "robot": {
                    "robot_id": robot_db.robot_id,
                    "battery_level": robot.battery_level,
                    "zone": zone,
                    "row": row_number,
                    "shelf": shelf_number,
                    "status": robot_db.status,
                    "last_update": (robot_db.last_update or scanned_at_ts).isoformat(),
                },
                "ingested_records": inserted_records_count,
                "created_new_robot": created_flag,
            }

            logger.info(
                "robot.ingest_done",
                robot_id=robot_db.robot_id,
                created_new_robot=created_flag,
                ingested_records=inserted_records_count,
            )
            return response

        except SQLAlchemyError as e:
            logger.exception("robot.ingest_failed", robot_id=robot.robot_id, error=str(e))
            raise RuntimeError("Failed to process robot data transactionally") from e
        # НЕТ session.close(): управление жизненным циклом — у DI/Depends

    async def register_robot(self, data: RobotRegisterRequest) -> RobotRegisterResponse:
        zone = data.zone or "A"
        row_number = data.row if data.row is not None else 0
        shelf_number = data.shelf if data.shelf is not None else 0
        battery_level = data.battery_level if data.battery_level is not None else 100.0
        status = data.status or "online"
        now_ts = datetime.now(timezone.utc)

        fake_robot_base = RobotBase(
            robot_id=data.robot_id,
            last_update=now_ts,
            location=Location(zone=zone, row=row_number, shelf=shelf_number),
            scan_results=[],
            battery_level=battery_level,
            next_checkpoint="INIT",
            status=status,
        )

        session = self.history_repo.session
        self.robot_repo.session = session  # жёсткое выравнивание

        try:
            async with session.begin():
                robot_db, created_flag = await self.robot_repo.upsert_robot(fake_robot_base)
                await session.flush()

            robot_token = SecurityManager.create_access_token(
                subject=robot_db.robot_id,
                token_type="robot",
                expires_delta=None,
            )
            return RobotRegisterResponse(
                robot_id=robot_db.robot_id,
                status=robot_db.status or "online",
                registered_at=now_ts,
                token=robot_token,
                create_flag=created_flag,
            )
        except SQLAlchemyError as e:
            logger.exception("robot.register_failed", robot_id=data.robot_id, error=str(e))
            raise RuntimeError("Failed to register robot") from e
        # НЕТ session.close()

    async def get_all_robots(self) -> RobotsListResponse:
        """
        Возвращает компактный список всех роботов.
        """
        # Сессионный цикл управляется DI, вручную не закрываем
        rows = await self.robot_repo.get_all()
        items: List[RobotForListOut] = [RobotForListOut(**row) for row in rows]
        return RobotsListResponse(total=len(items), items=items)
