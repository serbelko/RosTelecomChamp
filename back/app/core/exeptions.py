# app/core/exceptions.py
from fastapi import HTTPException, status


class AuthException(HTTPException):
    """Base authentication exception."""
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(status_code=status_code, detail=detail)


class InvalidCredentialsException(AuthException):
    def __init__(self, problem: str):
        super().__init__(f"Invalid credentials: {problem}")


class TokenExpiredException(AuthException):
    def __init__(self):
        super().__init__("Token has expired")


class InvalidTokenException(AuthException):
    def __init__(self):
        super().__init__("Invalid token")


class UserNotFoundException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


class UserAlreadyExistsException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )


class RateLimitExceededException(HTTPException):
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds",
            headers={"Retry-After": str(retry_after)}
        )


class StrongPasswordException(AuthException):
    def __init__(self):
        super().__init__("Password is not strong")


class InvalidVerifyTokenException(AuthException):
    def __init__(self):
        super().__init__("Invalid verification token for email/pwd")


class InvalidPasswordExepiton(AuthException):
    def __init__(self, status_code = status.HTTP_401_UNAUTHORIZED):
        super().__init__("Email or Password is Incorrect")