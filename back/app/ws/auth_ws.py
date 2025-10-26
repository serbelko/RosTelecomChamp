from fastapi import WebSocket, WebSocketException, status
import structlog

from app.core.security import SecurityManager

logger = structlog.get_logger(__name__)


async def authenticate_websocket(websocket: WebSocket) -> str:
    """
    Проверяем JWT из заголовка Authorization: Bearer <token>.
    Возвращаем user_id (payload["sub"]) или рвём соединение с кодом 1008.
    """

    auth_header = websocket.headers.get("Authorization")
    if not auth_header:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Missing Authorization header"
        )

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid Authorization header format"
        )

    token = parts[1]

    payload = SecurityManager.verify_token(token)
    if payload is None:
        # Токен сломан / протух / подписан другим SECRET_KEY
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or expired token"
        )

    user_id = payload.get("sub")
    if not user_id:
        # Наш контракт: sub обязан быть user_id
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid token payload (no sub)"
        )

    logger.info("ws_auth_ok", user_id=user_id)
    return user_id
