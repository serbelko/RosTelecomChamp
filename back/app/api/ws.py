# app/api/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

from app.ws.connection_manager import connection_manager
from app.ws.auth_ws import authenticate_websocket

logger = structlog.get_logger(__name__)

ws_router = APIRouter()


@ws_router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    # 1. Проверяем токен и выясняем user_id
    try:
        user_id = await authenticate_websocket(websocket)
    except Exception as e:
        # Если токен невалидный, сюда попадет WebSocketException из authenticate_websocket
        # FastAPI сам отправит close с кодом 1008 и reason
        logger.warning("ws_auth_failed", error=str(e))
        raise

    # 2. Принимаем соединение (гарантированно после успешной аутентификации)
    await websocket.accept()

    # 3. Регистрируем соединение пользователя в менеджере
    await connection_manager.connect(user_id, websocket)

    try:
        # 4. Основной цикл взаимодействия с клиентом
        while True:
            # Ждем сообщение от клиента
            data = await websocket.receive_json()

            # Тут можно реализовать протокол сообщений от клиента
            # Например клиент может просить подписку на конкретного робота
            # data может выглядеть так:
            # {"action": "subscribe", "robot_id": "RB-001"}

            logger.info("ws_client_message", user_id=user_id, data=data)

            # Можно тут же отправить что-то обратно
            await websocket.send_json({
                "type": "ack",
                "received": data,
            })

    except WebSocketDisconnect:
        logger.info("ws_disconnected_by_client", user_id=user_id)
    except Exception as e:
        logger.warning("ws_error", user_id=user_id, error=str(e))
        # при любой ошибке вылетаем и отключаем сокет
    finally:
        # 5. Убираем соединение из менеджера
        connection_manager.disconnect(user_id, websocket)
        # Явно закрывать websocket не обязательно, если это был WebSocketDisconnect
        # Если хочешь жёстко: await websocket.close()
