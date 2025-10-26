from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List


class ScanResult(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    status: str


class Location(BaseModel):
    zone: str
    row: int
    shelf: int


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

