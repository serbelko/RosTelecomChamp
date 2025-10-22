from bson import ObjectId
from sqlalchemy import select
from app.db.base import Base, Users
from app.schemas.user import DbUser, UserUpdate, DbUser
from typing import Optional
from app.db.base import Users
from datetime import datetime
import structlog    

logger = structlog.get_logger(__name__)


class UserRepository:
    def __init__(self, db: Base):
        self.db = db
    
    async def create_user(self, payload: DbUser) -> Users:
        user = Users(
            id=payload.id,
            email=payload.email,
            password_hash=payload.password_hash,
            user_name=payload.user_name,
            role=payload.role,
        )
        self.db.add(user)
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.info("User create conflict", email=payload.email)
            raise ValueError("User with this email already exists", e) from e

        await self.db.refresh(user)
        logger.info("User created", user_id=str(user.id), email=user.email)
        return user
    
    async def get_by_id(self, user_id: int) -> DbUser:
        result = await self.db.execute(select(Users).where(Users.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> DbUser:
        result = await self.db.execute(select(Users).where(Users.email == email))
        return result.scalar_one_or_none()
