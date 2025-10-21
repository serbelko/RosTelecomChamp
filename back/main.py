from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.session import engine
from app.db.base import Base
from app.api import health_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(title="Backend", lifespan=lifespan)
app.include_router(health_router)
