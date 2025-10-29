from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 👈 добавлено для CORS
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

    app.include_router(health.router)
    app.include_router(user.router, prefix="/api")
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
