from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
