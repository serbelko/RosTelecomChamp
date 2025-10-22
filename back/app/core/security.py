from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

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
        Создаёт подписанный JWT.
        Поля (стандартные и полезные):
          - sub: кому выдан
          - exp: истечение
          - iat: когда выдан
          - nbf: не раньше
          - iss: издатель (если задан)
          - aud: аудитория (если задана)
          - type: тип токена (access/refresh)
        """
        now = SecurityManager._now()
        expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

        to_encode: dict[str, Any] = {
            "sub":  subject,
            "type": "access",
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int(expire.timestamp()),
        }

        if getattr(settings, "ISSUER", None):
            to_encode["iss"] = settings.ISSUER
        if getattr(settings, "AUDIENCE", None):
            to_encode["aud"] = settings.AUDIENCE

        token = jwt.encode(
            claims=to_encode,
            key=settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,   # например HS256
        )
        return token

    @staticmethod
    def verify_token(token: str) -> Optional[dict[str, Any]]:
        """
        Валидирует и декодирует JWT.
        Возвращает payload или None, если подпись/срок/аудитория/издатель не проходят.
        """
        options = {
            "verify_aud": bool(getattr(settings, "AUDIENCE", None)),
        }
        try:
            payload = jwt.decode(
                token=token,
                key=settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                audience=getattr(settings, "AUDIENCE", None),
                issuer=getattr(settings, "ISSUER", None),
                options=options,
            )
            return payload
        except JWTError as e:
            logger.warning("JWT verification failed", error=str(e))
            return None

    # Пароли, оставляем как было
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

