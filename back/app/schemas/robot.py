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
    status: str|None = None


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
    status: str|None = None

    model_config = ConfigDict(from_attributes=True)


class RobotRegisterRequest(BaseModel):
    robot_id: str = Field(..., description="Уникальный ID робота, например 'RB-001'")

    zone: Optional[str] = Field(
        default=None,
        description="Стартовая зона (если не указано — 'A')",
        examples=["A"],
    )
    row: Optional[int] = Field(
        default=None,
        description="Стартовая строка/ряд (если не указано — 0)",
        examples=[10],
    )
    shelf: Optional[int] = Field(
        default=None,
        description="Стартовая полка (если не указано — 0)",
        examples=[3],
    )

    battery_level: Optional[float] = Field(
        default=None,
        description="Текущий заряд батареи в %, если не указано — 100.0",
        examples=[87.5],
    )

    status: Optional[str] = Field(
        default=None,
        description="Статус робота ('online', 'offline', 'error'). По умолчанию 'online'.",
    )


class RobotRegisterResponse(BaseModel):
    robot_id: str
    status: str
    registered_at: datetime
    token: str = Field(
        ...,
        description="JWT токен робота (type='robot'). Передавать как Authorization: Bearer <token>",
    )
