from __future__ import annotations

from datetime import datetime
from typing import Iterable, Dict, Any, Optional
from fastapi import APIRouter

from app.ws.connection_manager import connection_manager

websocket_router = APIRouter()


def build_robot_update(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ожидаем словарь такого вида, который формируется в RobotService.process_robot_data():

    {
        "robot_id": "RB-001",
        "battery_level": 97.3,
        "zone": "A",
        "row": 7,
        "shelf": 2,
        "last_update": "2025-10-28T22:48:53.089237",
    }

    Возвращаем WS-сообщение, унифицированное для фронтенда.
    """
    return {
        "type": "robot_update",
        "robot_id": payload.get("robot_id"),
        "battery_level": payload.get("battery_level"),
        "status": "active",  # можно доработать в будущем, если будут статусы робота
        "last_update": payload.get("last_update"),
        "location": {
            "zone": payload.get("zone"),
            "row": payload.get("row"),
            "shelf": payload.get("shelf"),
        },
        # Можно добавить "next_checkpoint", если ты потом захочешь это передавать
        # "next_checkpoint": payload.get("next_checkpoint"),
    }


def build_inventory_alert(
    zone: str,
    product_ids: Iterable[str],
    severity: str,
    at: datetime,
) -> Dict[str, Any]:
    """
    Формат push-события об инвентаризации:
    - severity = "LOW" или "CRITICAL"
    - product_ids = список SKU
    """
    return {
        "type": "inventory_alert",
        "payload": {
            "zone": zone,
            "product_ids": list(product_ids),
            "severity": severity,
            "at": at.isoformat(),
        },
    }


async def notify_robot_update(
    robot_payload: Dict[str, Any],
    user_ids: Optional[Iterable[str]] = None,
) -> None:
    """
    Шлёт событие 'robot_update' через connection_manager.
    Теперь принимает словарь, а не Pydantic-модель.
    """

    msg = build_robot_update(robot_payload)

    if user_ids:
        # Точечная отправка
        for uid in user_ids:
            await connection_manager.send_to_user(uid, msg)
    else:
        # Широковещательно всем онлайновым пользователям
        await connection_manager.broadcast(msg)


async def notify_inventory_alert(
    zone: str,
    product_ids: Iterable[str],
    severity: str,
    at: datetime,
    user_ids: Optional[Iterable[str]] = None,
) -> None:
    """
    Шлёт событие 'inventory_alert' (например, CRITICAL остатки по зоне).
    """

    msg = build_inventory_alert(zone, product_ids, severity, at)

    if user_ids:
        for uid in user_ids:
            await connection_manager.send_to_user(uid, msg)
    else:
        await connection_manager.broadcast(msg)
