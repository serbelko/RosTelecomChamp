from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

router = APIRouter(prefix="/ping", tags=["health"])

@router.get("/", summary="Liveness probe")
async def ping():
    return {"status": "ok"}