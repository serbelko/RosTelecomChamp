from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.settings import settings

logger = structlog.get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityManager:
    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def create_access_token(
        subject: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Простой access JWT для фронта (HS256, без iss/aud).
        """
        now = SecurityManager._now()
        expire = now + (expires_delta or timedelta(
            minutes=(settings.ACCESS_TOKEN_EXPIRE_MINUTES or 45)
        ))

        to_encode: dict[str, Any] = {
            "sub":  subject,
            "type": "access",
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int(expire.timestamp()),
        }

        token = jwt.encode(
            claims=to_encode,
            key=settings.SECRET_KEY,
            algorithm=(settings.ALGORITHM or "HS256"),
        )
        return token

    @staticmethod
    def verify_token(token: str) -> Optional[dict[str, Any]]:
        """
        Валидирует подпись и сроки. Никаких aud/iss. Возвращает payload или None.
        """
        options = {
            "verify_aud": False,
            "leeway": 30,  # на всякий случай, чтобы кривые часы не ломали жизнь
        }
        try:
            payload = jwt.decode(
                token=token,
                key=settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM or "HS256"],
                options=options,
            )
            if payload.get("type") != "access":
                logger.warning("JWT type mismatch", actual=payload.get("type"))
                return None
            return payload
        except JWTError as e:
            logger.warning("JWT verification failed", error=str(e))
            return None
    

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        if len(password) < settings.PASSWORD_MIN_LENGTH:
            return False, f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long"
        return True, "Password is valid"
