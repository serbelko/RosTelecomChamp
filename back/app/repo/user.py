from bson import ObjectId
from app.db.base import Base, UsersORM
from app.schemas.user import DbUserCreate, UserCreate, UserUpdate
from typing import Optional
from datetime import datetime
import structlog    

logger = structlog.get_logger(__name__)


class UserRepository:
    def __init__(self, db: Base):
        self.db = db
    
    async def create_user(self, payload: DbUserCreate) -> UsersORM:
        user = UsersORM(
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
            raise ValueError("User with this email already exists") from e

        await self.db.refresh(user)
        logger.info("User created", user_id=str(user.id), email=user.email)
        return user
    

