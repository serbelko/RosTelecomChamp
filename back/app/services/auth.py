from app.repo.user import UserRepository
import uuid
from time import time
# from app.services.cache import CacheService
from app.core.security import SecurityManager
from app.schemas.user import DbUser, UserCreate
from app.schemas.request import RegisterRequest, LoginRequest, CheckTokenRequest
from app.schemas.token import Token
from app.core.exeptions import (
    InvalidCredentialsException,
    UserAlreadyExistsException,
    UserNotFoundException,
    InvalidTokenException,
    RateLimitExceededException,
    StrongPasswordException,
    InvalidVerifyTokenException,
    InvalidPasswordExepiton
)
from app.core.settings import settings
import structlog

logger = structlog.get_logger(__name__)


class AuthService:
    def __init__(
        self, 
        user_repo: UserRepository, 
        # cache_service: CacheService,
    ):
        self.user_repo = user_repo
        # self.cache_service = cache_service
        
    async def register_user(self, user_create: RegisterRequest) -> dict:
        """Register new user """
        existing_user = await self.user_repo.get_by_email(user_create.email)
        if existing_user:
            raise UserAlreadyExistsException()
        
        is_valid, _ = SecurityManager.validate_password_strength(user_create.password)
        if not is_valid:
            raise InvalidCredentialsException()
        

        data = user_create.model_dump()
        if 'password' in data:
            data['password_hash'] = SecurityManager.get_password_hash(data["password"])
            del data['password']
        data["id"] = uuid.uuid4()
        user = await self.user_repo.create_user(DbUser.model_validate(data))
        token = SecurityManager.create_access_token(str(user.id))
        
        
        logger.info(
            "User registered", 
            user_id=str(user.id), 
            email=user.email
        )
        
        return {
            "message": "User registered successfully. Please check your email to verify your account.",
            "user_id": str(user.id),
            "email": user.email,
            "verification_required": True,
            "token": token
        }

    async def login_user(self, user: LoginRequest) -> str:
        login_user = await self.user_repo.get_by_email(user.email)
        if not login_user:
            raise UserNotFoundException()
        
        if not SecurityManager.verify_password(user.password, login_user.password_hash):
            raise InvalidPasswordExepiton()
        
        token = SecurityManager.create_access_token(str(login_user.id))
        logger.info("auth.logged_in", user_id=str(login_user.id), email=user.email)
        return token
