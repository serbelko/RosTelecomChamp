from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.schemas.user import RegisterRequest
from passlib.hash import bcrypt
from app.db.base import User

router = APIRouter()

@router.post("/create", response_model=dict)
async def create_user(user_data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(User).where(User.email == user_data.email))
    if q.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email уже зарегистрирован")
    user = User(email=user_data.email, hashed_password=bcrypt.hash(user_data.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

