from pydantic import BaseModel, EmailStr, UUID4

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
    email: EmailStr | None = None
    password_hash: str | None = None
    user_name: str | None = None
    role: str | None = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
