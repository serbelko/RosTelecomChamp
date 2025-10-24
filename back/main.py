from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 👈 добавлено для CORS
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

    # 👇 ДОБАВЛЕНО: Разрешаем запросы с фронта (CORS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4200"],  # адрес фронтенда
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    container = Container()
    app.container = container
    container.wire(packages=["app.api"])

    # 👇 Роутеры подключаются после добавления CORS
    app.include_router(health_router)
    app.include_router(user_router, prefix="/api/v1")

    return app

app = create_app()

# ==============================
# ✅ ЧТО ДОБАВЛЕНО (Лёша):
# 1. Импорт:
#    from fastapi.middleware.cors import CORSMiddleware
#
# 2. Внутри create_app() перед роутерами:
#    app.add_middleware(
#        CORSMiddleware,
#        allow_origins=["http://localhost:4200"],
#        allow_credentials=True,
#        allow_methods=["*"],
#        allow_headers=["*"],
#    )
#
# 👉 Это включает CORS, чтобы Angular (http://localhost:4200)
#    мог без ошибок делать запросы к FastAPI на http://localhost:8000.
#
# ⚠️ Без этого браузер блокировал бы preflight-запросы OPTIONS.
# ==============================
