from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.session import engine
from app.db.base import Base
from app.core.container import Container
from app.api import health, user, robot, ws, inventory, dashboard, import_csv, export, ai
from app.core.middleware import AuthMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    container = Container()
    app.container = container
    container.wire(packages=["app.api"])

    cache_service = container.cache_service()
    await cache_service.connect()

    yield

    try:
        await cache_service.disconnect()
    except Exception:
        pass
    await engine.dispose()

def create_app() -> FastAPI:
    app = FastAPI(title="Backend", lifespan=lifespan)

    app.include_router(health.router)
    app.include_router(user.router)
    app.include_router(robot.router)
    app.include_router(ws.ws_router)
    app.include_router(inventory.router)
    app.include_router(dashboard.router)
    app.include_router(import_csv.router)
    app.include_router(export.router)
    app.include_router(ai.router)


    app.add_middleware(AuthMiddleware)
    return app

app = create_app()
