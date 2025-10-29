# app/schemas/robot.py

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Optional

class Location(BaseModel):
    zone: str
    row: int
    shelf: int

class ScanResult(BaseModel):
    product_id: str
    product_name: Optional[str] = None
    quantity: int
    status: Optional[str] = None  # "OK" | "LOW_STOCK" | "CRITICAL"

class RobotBase(BaseModel):
    robot_id: str
    last_update: datetime = Field(alias="timestamp")
    location: Location
    scan_results: List[ScanResult]
    battery_level: float
    next_checkpoint: str


    class Config:
        populate_by_name = True 
        from_attributes = True

class RobotOut(BaseModel):
    robot_id: str
    battery_level: float
    zone: str
    row: int
    shelf: int
    last_update: datetime

    model_config = ConfigDict(from_attributes=True)

