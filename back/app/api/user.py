from fastapi import APIRouter, status, Depends
from dependency_injector.wiring import inject, Provide
from app.core.container import Container
from app.services.auth import AuthService
from app.schemas.user import UserOut
from app.schemas.request import RegisterRequest, LoginRequest
from app.utils.deps import get_current_user, require_role

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/create", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@inject
async def create_user(
    payload: RegisterRequest,
    auth_service: AuthService = Depends(Provide[Container.auth_service]),
):
    new = await auth_service.register_user(payload)
    return {"token": new["token"]}


@router.post("/login", response_model=UserOut, status_code=status.HTTP_200_OK)
@inject
async def login_user(
    payload: LoginRequest,
    auth_service: AuthService = Depends(Provide[Container.auth_service]),):

    token = await auth_service.login_user(payload)
    return {"token": token}


@router.get("/me")
async def me(current = Depends(get_current_user)):
    return {"id": str(current.id), "email": current.email, "role": current.role}

@router.get("/admin-only")
async def admin_only(current = Depends(require_role("admin"))):
    return {"ok": True}
