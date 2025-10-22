from pydantic import BaseModel, EmailStr, UUID4

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class DbUser(BaseModel):
    id: str | UUID4 | None = None
    email: EmailStr
    password_hash: str
    user_name: str | None = None
    role: str | None = None
    created_at: str | None = None

class UserOut(BaseModel):
    token: str

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    is_active: bool | None = None
    is_verified: bool | None = None
    hashed_password: str | None = None
    email: EmailStr | None = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
