# app/core/container.py

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.settings import settings

from app.repo.user import UserRepository
from app.repo.robot import RobotRepository
from app.repo.inventory import InventoryHistoryRepository
from app.repo.product import ProductRepository

from app.services.auth import AuthService
from app.services.cache import CacheService
from app.services.robot import RobotService
from app.services.history import HistoryService
from app.services.dashboard import DashboardService
from app.services.import_inventory import InventoryImportService
from app.services.export_service import ExportService
from app.services.ai import AIService


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        packages=["app.api"]
    )

    engine = providers.Singleton(
        create_async_engine,
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        future=True,
        pool_size=30,
    )

    async_session_factory = providers.Singleton(
        sessionmaker,
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async_session = providers.Factory(
        lambda factory: factory(),
        async_session_factory
    )
    cache_service = providers.Singleton(CacheService)
    # # message_broker = providers.Singleton(MessageBroker)

    # repos
    user_repository = providers.Factory(
        UserRepository,
        db=async_session,
    )

    robot_repository = providers.Factory(
        RobotRepository,
        db=async_session,
    )

    product_repository = providers.Factory(
        ProductRepository,
        session=async_session,  # <- важно: параметр назови как в __init__
    )

    inventory_repository = providers.Factory(
        InventoryHistoryRepository,
        session=async_session,
    )

    # services
    auth_service = providers.Factory(
        AuthService,
        user_repo=user_repository,
    )

    history_service = providers.Factory(
        HistoryService,
        repo=inventory_repository,
    )

    robot_service = providers.Factory(
        RobotService,
        robot_repo=robot_repository,
        product_repo=product_repository,
        history_repo=inventory_repository,
    )

    dashboard_service = providers.Factory(
        DashboardService,
        robot_repo=robot_repository,
        history_repo=inventory_repository,
    )
    inventory_import_service = providers.Factory(
        InventoryImportService,
        history_repo=inventory_repository,
    )

    export_service = providers.Factory(
        ExportService,
        history_repo=inventory_repository,
    )

    ai_service = providers.Factory(
        AIService,
        product_repo=product_repository,
    )
