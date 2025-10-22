from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.session import engine
from app.db.base import Base
from app.core.container import Container
from app.api import health_router, user_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

def create_app() -> FastAPI:
    app = FastAPI(title="Backend", lifespan=lifespan)

    container = Container()
    app.container = container
    container.wire(packages=["app.api"])
    app.include_router(health_router)                # /ping/
    app.include_router(user_router, prefix="/api/v1")# /api/v1/...


    return app
app = create_app()
