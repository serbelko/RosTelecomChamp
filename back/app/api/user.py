from fastapi import APIRouter, Depends, Request, status
router = APIRouter()

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.schemas.user import RegisterRequest

router = APIRouter()

@router.post("/create", summary="Проверка подключения к PostgreSQL", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_user(request: Request,
    user_data: RegisterRequest,
    db: AsyncSession = Depends(get_db)):
    
    result = db.