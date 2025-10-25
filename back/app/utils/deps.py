
from fastapi import Header, HTTPException, Depends, status
from dependency_injector.wiring import Provide, inject
from app.core.container import Container
from app.core.security import SecurityManager
from app.repo.user import UserRepository

def get_bearer(authorization: str = Header("")) -> str:
    """Использовать для аутентификации юзера"""
    # допускаем разный регистр "Bearer"
    if not authorization or " " not in authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scheme, token = authorization.split(" ", 1)
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token.strip()

async def get_current_user(
    token: str = Depends(get_bearer),
    repo: UserRepository = Depends(Provide[Container.user_repository]),
):
    payload = SecurityManager.verify_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]     # у тебя sub = id или email, смотри как генеришь
    user = await repo.get_by_id(user_id)
    if not user:
        # токен валидный, но пользователь уже не существует
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# 3) гард по ролям
def require_role(*allowed: str):
    async def dep(current = Depends(get_current_user)):
        if current.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return current
    return dep
