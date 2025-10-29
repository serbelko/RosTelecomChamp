from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import structlog
from sqlalchemy.exc import SQLAlchemyError

from app.repo.robot import RobotRepository
from app.repo.inventory import InventoryHistoryRepository
from app.repo.product import ProductRepository
from app.core.security import SecurityManager
from app.schemas.robot import RobotBase, RobotRegisterRequest, RobotRegisterResponse, Location
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
        Обработка данных робота в одной транзакции:
        1. upsert робота (создать или обновить)
        2. гарантировать наличие продуктов
        3. сохранить сканы в inventory_history
        4. commit
        5. отправить WebSocket события (после коммита)
        """

        # === 0. Нормализация входных данных ===
        scanned_at_ts: datetime = robot.last_update or datetime.now(timezone.utc)

        zone = robot.location.zone
        row_number = robot.location.row
        shelf_number = robot.location.shelf

        scan_results = robot.scan_results or []

        logger.info(
            "robot.ingest_start",
            robot_id=robot.robot_id,
            zone=zone,
            row=row_number,
            shelf=shelf_number,
            battery=robot.battery_level,
            scans=len(scan_results),
        )

        # Нам нужно понять: сколько записей реально попало в историю
        inserted_records_count = 0

        # =========================================================
        # === 1-3. Все изменения в рамках одной транзакции      ===
        # =========================================================
        try:
            # 1. upsert робота
            #    (создаём или обновляем робота)
            robot_db, created_flag = await self.robot_repo.upsert_robot(robot)
            # robot_db — это ORM-объект Robots из сессии
            # created_flag — True если создавали нового

            # 2. гарантируем, что все товары есть в products
            products_map: Dict[str, str] = {}
            for scan in scan_results:
                if not scan.product_id:
                    continue
                products_map[scan.product_id] = scan.product_name or scan.product_id

            if products_map:
                # ensure_products_exist должна добавлять недостающие продукты в эту же сессию
                await self.product_repo.ensure_products_exist(products_map)
                

            # 3. формируем записи инвентаризации
            records_to_create: List[InventoryRecordCreate] = []
            for item in scan_results:
                status_norm = item.status.upper() if item.status else None

                record = InventoryRecordCreate(
                    robot_id=robot.robot_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    zone=zone,
                    row_number=row_number,
                    shelf_number=shelf_number,
                    status=status_norm,
                    scanned_at=scanned_at_ts,
                )
                records_to_create.append(record)

            if records_to_create:
                await self.history_repo.create_many(records_to_create)
                # опять же — без коммита

                inserted_records_count = len(records_to_create)

            # --- На этом этапе в сессии есть:
            # - новый/обновлённый робот
            # - новые продукты (если создавались)
            # - новые записи истории
            # Но они ещё НЕ зафиксированы в базе.

            # Теперь делаем общий commit
            # Важно: мы должны понимать, что все репозитории
            # используют одну и ту же сессию (например, переданную через DI).
            await self.history_repo.session.commit()

        except SQLAlchemyError as e:
            # В случае любой ошибки — откатываем ВСЁ
            # Откатываем через любую из сессий, они должны быть одинаковые —
            # берём history_repo.session как представителя
            await self.history_repo.session.rollback()

            logger.exception(
                "robot.ingest_failed",
                robot_id=robot.robot_id,
                error=str(e),
            )
            raise RuntimeError("Failed to process robot data transactionally") from e

        # =========================================================
        # === 4. Успешный коммит — теперь можно слать ивенты WS ===
        # =========================================================

        # после commit() ORM-объект robot_db всё ещё живой (он привязан к сессии),
        # у него есть финальные значения, в т.ч. те, что в базе.
        try:
            await notify_robot_update({
                "robot_id": robot_db.robot_id,
                "battery_level": robot_db.battery_level,
                "zone": robot_db.zone,
                "row": robot_db.row,
                "shelf": robot_db.shelf,
                "status": robot_db.status or "active",
                "last_update": (robot_db.last_update or scanned_at_ts).isoformat(),
                "next_checkpoint": robot.next_checkpoint,
            })
        except Exception as e:
            logger.warning(
                "ws.robot_update_failed",
                robot_id=robot.robot_id,
                error=str(e),
            )

        # Собираем продукты с CRITICAL / LOW
        critical_ids = [
            scan.product_id
            for scan in scan_results
            if scan.status and scan.status.upper() in ("CRITICAL", "CRIT")
        ]

        low_ids = [
            scan.product_id
            for scan in scan_results
            if scan.status and scan.status.upper() in ("LOW_STOCK", "LOW")
        ]

        now = datetime.now(timezone.utc)

        try:
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
        except Exception as e:
            logger.warning(
                "ws.alert_failed",
                robot_id=robot.robot_id,
                critical_items=critical_ids,
                low_items=low_ids,
                error=str(e),
            )

        # =========================================================
        # === 5. Ответ клиенту                                 ===
        # =========================================================
        response = {
            "robot": {
                "robot_id": robot_db.robot_id,
                "battery_level": robot_db.battery_level,
                "zone": robot_db.zone,
                "row": robot_db.row,
                "shelf": robot_db.shelf,
                "status": robot_db.status,
                "last_update": (robot_db.last_update or scanned_at_ts).isoformat(),
            },
            "ingested_records": inserted_records_count,
            "created_new_robot": created_flag,
        }

        logger.info(
            "robot.ingest_done",
            robot_id=robot.robot_id,
            created_new_robot=created_flag,
            ingested_records=inserted_records_count,
        )

        return response
    
    async def register_robot(self, data: RobotRegisterRequest) -> RobotRegisterResponse:
        """
        Регистрирует нового робота (или обновляет поле состояния),
        и генерирует ему роботский JWT токен.
        Если каких-то полей нет — проставляем безопасные значения по умолчанию.
        """

        # Подготовка дефолтов для обязательных в БД полей
        zone = data.zone or "A"
        row_number = data.row if data.row is not None else 0
        shelf_number = data.shelf if data.shelf is not None else 0
        battery_level = data.battery_level if data.battery_level is not None else 100.0
        status = data.status or "online"

        now_ts = datetime.now(timezone.utc)

        # Собираем временный RobotBase, чтобы переиспользовать механизм upsert_robot()
        fake_robot_base = RobotBase(
            robot_id=data.robot_id,
            last_update=now_ts,
            location=Location(
                zone=zone,
                row=row_number,
                shelf=shelf_number,
            ),
            scan_results=[],  # регистрации нет инвентаризации
            battery_level=battery_level,
            next_checkpoint="INIT",
            status=status,
        )

        # Пробуем сохранить робота в БД
        try:
            robot_db, created_flag = await self.robot_repo.upsert_robot(fake_robot_base)

            # фиксируем изменения в рамках сессии
            await self.history_repo.session.commit()

        except SQLAlchemyError as e:
            await self.history_repo.session.rollback()
            logger.exception(
                "robot.register_failed",
                robot_id=data.robot_id,
                error=str(e),
            )
            raise RuntimeError("Failed to register robot") from e

        # Генерируем токен для робота: type='robot'
        robot_token = SecurityManager.create_access_token(
            subject=robot_db.robot_id,
            token_type="robot",
            expires_delta=None,  # Можно сделать TTL отдельно
        )

        return RobotRegisterResponse(
            robot_id=robot_db.robot_id,
            status=robot_db.status or "online",
            registered_at=now_ts,
            token=robot_token,
        )