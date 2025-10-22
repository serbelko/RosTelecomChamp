from fastapi import APIRouter, status, Depends
from dependency_injector.wiring import inject, Provide
from app.core.container import Container
from app.services.auth import AuthService
from app.schemas.user import RegisterRequest, UserOut

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/create", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@inject
async def create_user(
    payload: RegisterRequest,
    auth_service: AuthService = Depends(Provide[Container.auth_service]),
):
    new = await auth_service.register_user(payload)
    return {"token": new["token"]}

