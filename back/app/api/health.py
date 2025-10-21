from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter(prefix="/ping", tags=["health"])

@router.get("/", summary="Проверка подключения к PostgreSQL")
async def ping_postgres(db: AsyncSession = Depends(get_db)):
    try:
        # выполняем простейший SQL-запрос
        result = await db.execute(text("SELECT 1"))
        value = result.scalar_one()
        if value == 1:
            return {"status": "ok", "postgres": "alive"}
        raise Exception("Unexpected result from database")
    except Exception as e:
        # если база недоступна, возвращаем ошибку
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {type(e).__name__}: {e}"
        )
