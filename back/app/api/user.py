from fastapi import APIRouter, status, Depends, Request, HTTPException
from dependency_injector.wiring import inject, Provide
from app.core.container import Container
from app.services.auth import AuthService
from app.schemas.user import UserOut, UserCreate
from app.schemas.request import RegisterRequest, LoginRequest
from app.utils.deps import get_current_user, require_role

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/create", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@inject
async def create_user(
    payload: UserCreate,
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
def get_me(request: Request):
    user_ctx = getattr(request.state, "current_user", None)
    if user_ctx is None:
        # сюда мы попадаем если:
        # - мидлвара не подключена
        # - этот эндпоинт вдруг оказался в open_paths
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    return {
        "user_id": user_ctx["user_id"],
        "claims": user_ctx["token_payload"],
    }