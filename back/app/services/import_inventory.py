# app/services/inventory_import.py
from __future__ import annotations

import csv
from io import StringIO
from typing import List, Tuple
from datetime import datetime

from app.schemas.import_inventory import InventoryImportRow, InventoryImportResult
from app.schemas.inventory import InventoryRecordCreate
from app.repo.inventory import InventoryHistoryRepository


class InventoryImportService:
    def __init__(self, history_repo: InventoryHistoryRepository):
        self.history_repo = history_repo

    async def import_csv(self, csv_text: str) -> InventoryImportResult:
        """
        Парсит CSV текст, валидирует строки, вставляет в БД,
        и возвращает результат.
        """

        reader = csv.DictReader(StringIO(csv_text))

        valid_records: List[InventoryRecordCreate] = []
        errors: List[str] = []

        line_number = 1  # для сообщений об ошибках, с учётом заголовка
        for row in reader:
            line_number += 1
            try:
                # Парсим строку через Pydantic
                parsed = InventoryImportRow(**row)

                # Готовим объект для записи в БД
                rec = InventoryRecordCreate(
                    robot_id=parsed.robot_id,
                    product_id=parsed.product_id,
                    quantity=parsed.quantity,
                    zone=parsed.zone,
                    row_number=parsed.row,
                    shelf_number=parsed.shelf,
                    status=parsed.status,
                    scanned_at=parsed.scanned_at,
                )
                valid_records.append(rec)

            except Exception as e:
                errors.append(f"Line {line_number}: {e}")

        # Пишем в БД все валидные строки
        success_count = 0
        if valid_records:
            try:
                await self.history_repo.create_many(valid_records)
                await self.history_repo.session.commit()
                success_count = len(valid_records)
            except Exception as e:
                # Если всё упало на коммите (например, FK нарушена),
                # откатим транзакцию и пометим всю партию как неуспешную.
                await self.history_repo.session.rollback()
                errors.append(f"DB commit failed: {e}")

        failed_count = len(errors)

        return InventoryImportResult(
            success=success_count,
            failed=failed_count,
            errors=errors,
        )
