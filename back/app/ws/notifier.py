# app/ws/notifier.py
from __future__ import annotations
from datetime import datetime
from typing import Iterable, Dict, Any, Optional
from app.ws.connection_manager import connection_manager

from datetime import datetime
from app.schemas.robot import RobotBase

def build_robot_update(robot: RobotBase) -> dict:
    loc = robot.location  # Location
    return {
        "type": "robot_update",
        "robot_id": robot.robot_id,
        "battery_level": robot.battery_level,
        "status": "active",
        "last_update": robot.last_update.isoformat(),   # alias 'timestamp' только на вход
        "location": {
            "zone": getattr(loc, "zone", None),
            "row": getattr(loc, "row", None),
            "shelf": getattr(loc, "shelf", None),
        },
        "next_checkpoint": robot.next_checkpoint,
    }


def build_inventory_alert(zone: str, product_ids: Iterable[str], severity: str, at: datetime) -> Dict[str, Any]:
    return {
        "type": "inventory_alert",
        "payload": {
            "zone": zone,
            "product_ids": list(product_ids),
            "severity": severity,  # "LOW" | "CRITICAL"
            "at": at.isoformat(),
        },
    }

async def notify_robot_update(robot, user_ids: Optional[Iterable[str]] = None) -> None:
    msg = build_robot_update(robot)
    if user_ids:
        # адресно
        for uid in user_ids:
            await connection_manager.send_to_user(uid, msg)
    else:
        # всем онлайн
        await connection_manager.broadcast(msg)

async def notify_inventory_alert(zone: str, product_ids: Iterable[str], severity: str, at: datetime, user_ids: Optional[Iterable[str]] = None) -> None:
    msg = build_inventory_alert(zone, product_ids, severity, at)
    if user_ids:
        for uid in user_ids:
            await connection_manager.send_to_user(uid, msg)
    else:
        await connection_manager.broadcast(msg)
