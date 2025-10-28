from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.session import engine
from app.db.base import Base
from app.core.container import Container
from app.api import health, user, robot, ws
from app.core.middleware import AuthMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

async def create_app() -> FastAPI:
    app = FastAPI(title="Backend", lifespan=lifespan)

    container = Container()
    app.container = container
    container.wire(packages=["app.api"])
    # Connect to cache
    cache_service = container.cache_service()
    await cache_service.connect()

    app.include_router(health.router)                # /ping/
    app.include_router(user.router, prefix="/api/v1")# /api/v1/...
    app.include_router(robot.router,prefix="/api/v1")

    app.include_router(ws.ws_router)
    app.add_middleware(AuthMiddleware)
    for route in app.router.routes:
        print("ROUTE:", getattr(route, "path", None), getattr(route, "methods", None), route)

    return app

app = create_app()
