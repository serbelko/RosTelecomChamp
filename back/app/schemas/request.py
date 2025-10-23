# app/schemas/request - сюда писать все возможные request
from pydantic import BaseModel, EmailStr


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


