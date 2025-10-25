from pydantic import BaseModel, EmailStr, UUID4

class RobotCreate(BaseModel):
    id: str | UUID4 | None = None
    robot_id: str
    status: str
    battery_level: int
    current_zone: str
    current_row: int
    current_shelf: int

class RobotUpdate(BaseModel):
    robot_id: str
    status: str
    battery_level: int
    last_update: str
    current_zone: str
    current_row: int
    current_shelf: int

    class Config:
        from_attributes = True



