# app/core/robot_middleware.py

from __future__ import annotations

from typing import Optional, Set
import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.security import SecurityManager

logger = structlog.get_logger(__name__)


class RobotAuthMiddleware(BaseHTTPMiddleware):
    """
    Проверяет аутентификацию робота для определённых путей.
    Ожидает JWT токен с type="robot".
    """

    def __init__(self, app, protected_paths: Optional[Set[str]] = None):
        super().__init__(app)
        self.protected_paths = protected_paths or {
            "/robots/data",
        }

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path not in self.protected_paths:
            # Это не роботский путь — пропускаем дальше без проверки
            return await call_next(request)

        # Достаём заголовок
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization header missing (robot)"},
            )

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid Authorization header format (robot)"},
            )

        token = parts[1]

        # Проверяем токен. Теперь требуем type="robot".
        payload = SecurityManager.verify_token(token, allowed_types={"robot"})
        if payload is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired robot token"},
            )

        robot_id = payload.get("sub")
        if not robot_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "Malformed robot token: no 'sub'"},
            )

        request.state.current_robot = {
            "robot_id": robot_id,
            "token_payload": payload,
        }

        logger.bind(robot_id=robot_id).info("robot.authenticated")

        return await call_next(request)
