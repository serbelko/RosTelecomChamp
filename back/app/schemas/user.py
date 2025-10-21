from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class DbUserCreate(BaseModel):
    id: str
    email: EmailStr
    password_hash: str
    user_name = str | None
    role = str | None
    created_at = str | None

class UserOut(BaseModel):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    is_active: bool | None = None
    is_verified: bool | None = None
    hashed_password: str | None = None
    email: EmailStr | None = None
