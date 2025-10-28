from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

router = APIRouter(prefix="/inventory", tags=["inventory"])

@router.get("/history", summary="Get inventory history")
async def get_history():
    pass