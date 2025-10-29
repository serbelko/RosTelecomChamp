# app/schemas/request - сюда писать все возможные request
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime


class LoginRequest(BaseModel): 
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class ExitRequest(BaseModel):
    token: str

class EditUserRequest(BaseModel):
    token: str
    email: EmailStr | None = None
    password_hash: str | None = None
    user_name: str | None = None
    role: str | None = None

class CheckTokenRequest(BaseModel):
    token: str


class InventoryHistoryRequest(BaseModel):
    # фильтры
    dt_from: datetime | None = None
    dt_to: datetime | None = None
    zones: List[str] | None = None
    statuses: List[str] | None = None          # ["OK","LOW_STOCK","CRITICAL"]
    product_id: str | None = None
    q: str | None = None                       # поиск по product_id / zone / status

    # пагинация / сортировка
    limit: int = 50
    offset: int = 0
    sort_by: str = "scanned_at"                # scanned_at, product_id, zone, status, quantity...
    sort_dir: str = "desc"

class RobotIngestResult(BaseModel):
    robot: Dict[str, Any]
    ingested_records: int
    created_new_robot: bool


class RobotIngestResponse(BaseModel):
    detail: str
    result: Optional[RobotIngestResult] = None