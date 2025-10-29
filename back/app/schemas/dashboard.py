from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from app.schemas.robot import RobotOut
from app.schemas.inventory import InventoryRecordOut


class DashboardStatisticsOut(BaseModel):
    active_robots: int
    total_robots: int
    checked_today: int
    critical_skus: int
    avg_battery_level: float


class DashboardCurrentResponse(BaseModel):
    robots: List[RobotOut]
    recent_scans: List[InventoryRecordOut]
    statistics: DashboardStatisticsOut


class RobotInfo(BaseModel):
    robot_id: str
    status: Optional[str] = None
    battery_level: Optional[float] = None
    last_update: Optional[datetime] = None
    zone: Optional[str] = None
    row: Optional[int] = None
    shelf: Optional[int] = None


class RecentScanItem(BaseModel):
    id: int
    robot_id: Optional[str]
    product_id: str
    quantity: int
    status: Optional[str]
    zone: str
    row_number: Optional[int]
    shelf_number: Optional[int]
    scanned_at: datetime


class DashboardStatistics(BaseModel):
    total_robots: int
    offline_robots: int
    critical_items: int
    low_stock_items: int
    scans_last_hour: int


class DashboardResponse(BaseModel):
    robots: List[RobotInfo]
    recent_scans: List[RecentScanItem]
    statistics: DashboardStatistics