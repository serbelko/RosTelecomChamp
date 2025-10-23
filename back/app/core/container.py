from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.settings import settings

from app.repo.user import UserRepository
from app.services.auth import AuthService
# from app.services.cache import CacheService


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        packages=["app.api"]  # роутеры, где ты будешь юзать DI
    )

    # ---------------- CONFIG ----------------
    config = providers.Configuration()

    engine = providers.Singleton(
        create_async_engine,
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        future=True,
    )

    async_session_factory = providers.Singleton( # создаёт 
        sessionmaker,
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async_session = providers.Factory(
        lambda factory: factory(),
        async_session_factory
    )

    # ---------------- INFRA ----------------
    # cache_service = providers.Singleton(CacheService)
    # # message_broker = providers.Singleton(MessageBroker)

    # ---------------- REPOSITORIES ----------------
    user_repository = providers.Factory(
        UserRepository,
        db=async_session
    )

    # ---------------

    auth_service = providers.Factory(
        AuthService,
        user_repo=user_repository,
        # cache_service=cache_service,
    )
