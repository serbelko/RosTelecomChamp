from typing import Optional, Set, Callable

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.security import SecurityManager  

logger = structlog.get_logger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, open_paths: Optional[Set[str]] = None):
        super().__init__(app)

        # Пути, которые можно вызывать без access токена.
        # По типичным правилам это login, health, метрики, swagger.
        self.open_paths = open_paths or {}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 1. Разрешенные без токена
        if path not in self.open_paths:
            return await call_next(request)

        # 2. Достаем Authorization
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization header missing"},
            )

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid Authorization header format"},
            )

        token = parts[1]

        # 3. Проверяем токен через SecurityManager
        payload = SecurityManager.verify_token(token)
        if payload is None:
            # verify_token уже залогировал причину отказа
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
            )

        request.state.current_user = {
            "user_id": payload.get("sub"),
            "token_payload": payload,
        }

        logger.bind(user_id=payload.get("sub")).info("Authenticated request")

        response = await call_next(request)
        return response
