from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.settings import settings
from collections.abc import AsyncGenerator

engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,  
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
