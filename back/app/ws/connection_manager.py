# app/ws/connection_manager.py
from typing import Dict, Set, Any
from fastapi import WebSocket
import structlog

logger = structlog.get_logger(__name__)

class ConnectionManager:
    def __init__(self):
        # user_id -> множество активных сокетов
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        # Регистрируем нового клиента
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info("ws_connected", user_id=user_id, connections=len(self.active_connections[user_id]))

    def disconnect(self, user_id: str, websocket: WebSocket):
        # Удаляем сокет пользователя из реестра
        conns = self.active_connections.get(user_id)
        if not conns:
            return
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            # если больше нет подключений от этого юзера, чистим ключ
            self.active_connections.pop(user_id, None)
        logger.info("ws_disconnected", user_id=user_id)

    async def send_to_user(self, user_id: str, message: Any):
        # Отправить JSON конкретному пользователю
        conns = self.active_connections.get(user_id)
        if not conns:
            return
        for ws in list(conns):
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning("ws_send_failed", user_id=user_id, error=str(e))

    async def broadcast(self, message: Any):
        # Разослать всем онлайн
        for user_id, conns in self.active_connections.items():
            for ws in list(conns):
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.warning("ws_broadcast_failed", user_id=user_id, error=str(e))


# создаем один глобальный инстанс менеджера
connection_manager = ConnectionManager()
