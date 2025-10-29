from __future__ import annotations

from typing import List
from io import BytesIO
from datetime import datetime
from openpyxl import Workbook

from app.repo.inventory import InventoryHistoryRepository


class ExportService:
    def __init__(self, history_repo: InventoryHistoryRepository):
        self.history_repo = history_repo

    async def export_inventory_history_to_excel(self, ids: List[int]) -> bytes:
        """
        Возвращает Excel-файл (в памяти) как bytes.
        """
        records = await self.history_repo.get_by_ids(ids)

        wb = Workbook()
        ws = wb.active
        ws.title = "Inventory"

        # Заголовки
        ws.append([
            "id",
            "robot_id",
            "product_id",
            "quantity",
            "zone",
            "row_number",
            "shelf_number",
            "status",
            "scanned_at",
        ])

        for rec in records:
            ws.append([
                rec.id,
                rec.robot_id,
                rec.product_id,
                rec.quantity,
                rec.zone,
                rec.row_number,
                rec.shelf_number,
                rec.status,
                rec.scanned_at.isoformat() if rec.scanned_at else None,
            ])

        # Сохраняем в память
        stream = BytesIO()
        wb.save(stream)
        stream.seek(0)

        return stream.read()
