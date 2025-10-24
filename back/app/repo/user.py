from __future__ import annotations

import uuid
from typing import Optional, Sequence

import structlog
from sqlalchemy import select, delete, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Users
from app.schemas.user import DbUser, UserUpdate
from app.core.exeptions import UserNotFoundException, UserAlreadyExistsException

logger = structlog.get_logger(__name__)


def _as_uuid(v: uuid.UUID | str) -> uuid.UUID:
    return v if isinstance(v, uuid.UUID) else uuid.UUID(v)


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # CREATE
    async def create_user(self, payload: DbUser) -> Users:
        user = Users(
            id=payload.id,  # либо убери это, если в модели default=uuid.uuid4
            email=payload.email,
            password_hash=payload.password_hash,
            user_name=payload.user_name if payload.user_name else None,
            role=payload.role if payload.role else None,
        )
        self.db.add(user)
        try:
            await self.db.flush()   # чтобы получить id/RETURNING до коммита
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.warning(e)
            
            raise UserAlreadyExistsException() from e

        await self.db.refresh(user)
        logger.info("user.created", user_id=str(user.id), email=user.email)
        return user

    # READ
    async def get_by_id(self, user_id: uuid.UUID | str) -> Optional[Users]:
        uid = _as_uuid(user_id)
        res = await self.db.execute(select(Users).where(Users.id == uid))
        return res.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Users]:
        res = await self.db.execute(select(Users).where(Users.email == email))
        return res.scalar_one_or_none()

    async def exists_by_email(self, email: str) -> bool:
        res = await self.db.execute(select(Users.id).where(Users.email == email))
        return res.scalar_one_or_none() is not None

    async def list(self, *, limit: int = 50, offset: int = 0) -> Sequence[Users]:
        res = await self.db.execute(
            select(Users).order_by(Users.created_at.desc()).limit(limit).offset(offset)
        )
        return res.scalars().all()

    async def count(self) -> int:
        res = await self.db.execute(select(func.count()).select_from(Users))
        return int(res.scalar() or 0)

    # UPDATE
    async def change(self, user_id: uuid.UUID | str, patch: UserUpdate) -> Users:
        uid = _as_uuid(user_id)
        values = patch.model_dump(exclude_unset=True)
        protected = {"id", "created_at"}
        values = {k: v for k, v in values.items() if k not in protected}

        # блокируем строку (требует активной транзакции — она уже авто-открыта)
        res = await self.db.execute(
            select(Users).where(Users.id == uid).with_for_update()
        )
        user = res.scalar_one_or_none()
        if not user:
            raise UserNotFoundException()

        if values:
            for field, val in values.items():
                setattr(user, field, val)

            try:
                await self.db.flush()
                await self.db.commit()
            except IntegrityError as e:
                await self.db.rollback()
                logger.warning("user.update_conflict", user_id=str(uid), fields=list(values.keys()))
                raise UserAlreadyExistsException() from e
        else:
            # ничего не меняем — но убедимся, что транзакция чистая
            await self.db.rollback()

        await self.db.refresh(user)
        logger.info("user.updated", user_id=str(uid), changed=list(values.keys()))
        return user

    # DELETE
    async def delete_by_email(self, email: str) -> bool:
        res = await self.db.execute(delete(Users).where(Users.email == email))
        deleted = res.rowcount or 0
        if deleted:
            await self.db.commit()
        else:
            await self.db.rollback()
        logger.info("user.deleted_by_email", email=email, count=deleted)
        return deleted > 0

    async def delete_by_id(self, user_id: uuid.UUID | str) -> bool:
        uid = _as_uuid(user_id)
        res = await self.db.execute(delete(Users).where(Users.id == uid))
        deleted = res.rowcount or 0
        if deleted:
            await self.db.commit()
        else:
            await self.db.rollback()
        logger.info("user.deleted_by_id", user_id=str(uid), count=deleted)
        return deleted > 0
