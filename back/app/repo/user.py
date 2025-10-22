from bson import ObjectId
from app.db.base import Base, Users
from app.schemas.user import DbUserCreate, UserCreate, UserUpdate
from typing import Optional
from datetime import datetime
import structlog    

logger = structlog.get_logger(__name__)


class UserRepository:
    def __init__(self, db: Base):
        self.db = db
    
    async def create_user(self, payload: DbUserCreate) -> Users:
        user = Users(
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
    
    async def get_by_id(self, user_id: int) -> Optional[models.User]:
        return self.db.query(User).filter(models.User.id == user_id).first()

    async def get_by_email(self, email: str) -> Optional[models.User]:
        return self.db.query(models.User).filter(models.User.email == email).first()

    async def update_user(self, user_id: str, payload: UserUpdate) -> Optional[Users]:
        user = await self.db.get(Users, ObjectId(user_id))
        if not user:
            logger.info("User not found for update", user_id=user_id)
            return None
        
        for field, value in payload.dict(exclude_unset=True).items():
            setattr(user, field, value)
        
        self.db.add(user)
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error("User update failed", user_id=user_id, error=str(e))
            raise
        await self.db.refresh(user)
        logger.info("User updated", user_id=user_id)
        return user

