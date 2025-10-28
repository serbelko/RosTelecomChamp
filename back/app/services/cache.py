import json
from typing import Optional, Dict, Any, List

import redis.asyncio as redis
import structlog

from app.core.settings import settings

logger = structlog.get_logger(__name__)


class CacheService:
    """
    CacheService - это абстракция поверх Redis, через которую
    мы работаем с оперативным состоянием системы.

    Основные обязанности:
    - хранить последнее состояние робота (для realtime дашборда)
    - отдавать сводку по всем роботам
    - кешировать профиль пользователя (роль и права)
    - антиспам аварийных алертов
    - хранить предрасчитанную дашбордную статистику
    """

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None

    async def connect(self):
        """
        Устанавливает соединение с Redis и пингует его.
        Должна вызываться один раз при старте приложения.
        """
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,  # строки, а не bytes
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            self.redis_client = None

    async def disconnect(self):
        """
        Закрывает соединение с Redis.
        Должна вызываться на shutdown приложения.
        """
        if self.redis_client:
            await self.redis_client.close()

    # =========================
    # ВНУТРЕННИЕ ХЕЛПЕРЫ КЛЮЧЕЙ
    # =========================

    @staticmethod
    def _key_robot_state(robot_id: str) -> str:
        # Хранит последний статус конкретного робота
        return f"robot:state:{robot_id}"

    @staticmethod
    def _key_user_profile(user_id: str) -> str:
        # Кеш профиля пользователя (роль, разрешения), чтобы не ходить в БД каждый раз
        return f"user:profile:{user_id}"

    @staticmethod
    def _key_alert_last_sent(robot_id: str, alert_type: str) -> str:
        # Для антиспама аварийных алертов
        # alert_type, например: "low_battery", "stuck", "error_state"
        return f"alert:last_sent:{robot_id}:{alert_type}"

    @staticmethod
    def _key_dashboard_stats() -> str:
        # Предрассчитанные агрегаты (сколько роботов в ошибке и т.д.)
        return "dashboard:stats"

    # =========================
    # РОБОТЫ: ОПЕРАТИВНОЕ СОСТОЯНИЕ
    # =========================

    async def set_robot_state(
        self,
        robot_id: str,
        state: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Обновляет "последнее известное состояние" робота.

        state — это словарь вида:
        {
            "robot_id": "RB-005",
            "battery": 37,
            "x": 12.1,
            "y": 7.4,
            "state": "moving",
            "ts": "2025-10-26T14:50:10Z"
        }

        ttl_seconds:
            - если None: ключ живёт без ограничения
            - если задан: через сколько секунд Redis удалит этот ключ автоматически
              (может быть полезно, чтобы пропадали давно-мертвые роботы)
        """
        if not self.redis_client:
            return

        key = self._key_robot_state(robot_id)
        data = json.dumps(state)

        if ttl_seconds is not None:
            await self.redis_client.set(key, data, ex=ttl_seconds)
        else:
            await self.redis_client.set(key, data)

    async def get_robot_state(self, robot_id: str) -> Optional[Dict[str, Any]]:
        """
        Возвращает последнее состояние конкретного робота из Redis.
        Если такого робота нет в кеше — вернет None.
        """
        if not self.redis_client:
            return None

        key = self._key_robot_state(robot_id)
        raw = await self.redis_client.get(key)
        if raw is None:
            return None

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in robot state cache", key=key)
            return None

    async def get_all_robot_states(self) -> List[Dict[str, Any]]:
        """
        Возвращает список состояний всех роботов, которые сейчас есть в Redis.
        Это источник данных для дашборда "текущая картина склада".

        Механика:
        - Ищем все ключи robot:state:*
        - Достаём по ним значения
        - Парсим JSON
        """
        if not self.redis_client:
            return []

        pattern = self._key_robot_state("*")  # robot:state:*
        states: List[Dict[str, Any]] = []

        # SCAN-итератор чтобы не блокировать Redis даже если ключей много
        async for key in self.redis_client.scan_iter(match=pattern):
            raw_val = await self.redis_client.get(key)
            if not raw_val:
                continue
            try:
                parsed = json.loads(raw_val)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in robot state cache", key=key)
                continue
            states.append(parsed)

        return states

    # =========================
    # АНТИСПАМ / ДЕДУПЛИКАЦИЯ АВАРИЙ
    # =========================

    async def should_suppress_alert(
        self,
        robot_id: str,
        alert_type: str,
        ttl_seconds: int,
    ) -> bool:
        """
        Антиспам аварийных алертов.

        Поведение:
        - Мы хотим не слать один и тот же алерт (например "low_battery") каждую секунду.
        - Логика: если за последние ttl_seconds мы уже отправляли этот тип алерта для этого робота,
          то новое уведомление подавляем.

        Возвращает:
        - True  -> этот алерт надо подавить (мы уже слали недавно)
        - False -> алерт можно слать (и мы зафиксировали факт отправки)

        Как работает:
        - Пытаемся atomically сделать SETNX ключа alert:last_sent:{robot_id}:{alert_type}
          Если ключа не было -> мы его ставим и говорим "не подавлять"
          Если ключ уже есть -> "подавлять"
        - Потом ставим EXPIRE этому ключу = ttl_seconds
        """
        if not self.redis_client:
            # Если Redis недоступен, не подавляем аварии
            return False

        key = self._key_alert_last_sent(robot_id, alert_type)

        # SETNX (set if not exists)
        was_set = await self.redis_client.setnx(key, "1")
        if was_set:
            # мы первый раз за ttl_seconds шлем этот тип алерта
            await self.redis_client.expire(key, ttl_seconds)
            return False  # не подавлять

        # ключ уже есть -> недавно слали
        return True  # подавляем

    # =========================
    # КЕШ ПРОФИЛЯ ПОЛЬЗОВАТЕЛЯ (РОЛИ / ДОСТУПЫ)
    # =========================

    async def set_user_profile(
        self,
        user_id: str,
        profile: Dict[str, Any],
        ttl_seconds: int = 300,
    ) -> None:
        """
        Кладём профиль пользователя в Redis, чтобы не дергать БД на каждом запросе.
        Пример profile:
        {
            "user_id": "...",
            "role": "operator",
            "active": true,
            "permissions": ["view_dashboard", "ack_alerts"]
        }

        ttl_seconds по умолчанию 5 минут.
        Это нормально, потому что права и роли не скачут каждую секунду.
        Если админ меняет роль, мы можем вручную сбросить кеш.
        """
        if not self.redis_client:
            return

        key = self._key_user_profile(user_id)
        data = json.dumps(profile)

        await self.redis_client.set(key, data, ex=ttl_seconds)

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Возвращает профиль пользователя из кеша, либо None если его нет.

        Это используется в AuthMiddleware / зависимостях авторизации,
        чтобы быстро получить роль и права без запроса в Postgres.
        """
        if not self.redis_client:
            return None

        key = self._key_user_profile(user_id)
        raw = await self.redis_client.get(key)
        if raw is None:
            return None

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in user profile cache", key=key)
            return None

    async def invalidate_user_profile(self, user_id: str) -> None:
        """
        Сбрасывает кеш профиля пользователя.
        Это нужно, когда, например, мы изменили роль или заблокировали юзера.
        """
        if not self.redis_client:
            return
        key = self._key_user_profile(user_id)
        await self.redis_client.delete(key)

    # =========================
    # ДАШБОРДНЫЕ МЕТРИКИ (АГРЕГАТЫ)
    # =========================

    async def set_dashboard_stats(
        self,
        stats: Dict[str, Any],
        ttl_seconds: int = 5,
    ) -> None:
        """
        Кладём предрассчитанные метрики дашборда.
        Эти метрики обычно считает celery периодически (раз в N секунд),
        чтобы API мог отдавать их мгновенно без тяжелых запросов.

        Пример stats:
        {
            "robots_total": 42,
            "robots_alerting": 3,
            "avg_task_duration_sec": 27.4,
            "ts": "2025-10-26T14:50:00Z"
        }

        ttl_seconds по умолчанию короткий, например 5 секунд.
        Это значит что если воркер вдруг умрёт и перестанет обновлять метрики,
        то фронт быстро поймёт, что данные устарели.
        """
        if not self.redis_client:
            return

        key = self._key_dashboard_stats()
        data = json.dumps(stats)
        await self.redis_client.set(key, data, ex=ttl_seconds)

    async def get_dashboard_stats(self) -> Optional[Dict[str, Any]]:
        """
        Возвращает предрассчитанные метрики дашборда.
        Это будет дергать Redis, а не тяжелые агрегации по БД.

        Если ключа нет (нет свежих метрик) — вернем None.
        Фронт/бэкенд может в этом случае показать плейсхолдер или предупредить,
        что метрика временно недоступна.
        """
        if not self.redis_client:
            return None

        key = self._key_dashboard_stats()
        raw = await self.redis_client.get(key)
        if raw is None:
            return None

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in dashboard stats cache", key=key)
            return None
