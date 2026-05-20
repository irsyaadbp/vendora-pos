"""Authentication API routes.

Provides endpoints for user login, token refresh, and logout.
Refresh tokens are delivered and read via HTTP-only secure cookies.
"""

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.login_attempt_repository import LoginAttemptRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, LoginResponse, TokenResponse, UserInfo
from app.schemas.common import APIResponse
from app.services.auth_service import AuthService

router = APIRouter()


def _get_auth_service(session: AsyncSession) -> AuthService:
    """Construct an AuthService with all required repositories.

    Args:
        session: The async database session for the current request.

    Returns:
        A fully-initialized AuthService instance.
    """
    user_repo = UserRepository(session)
    refresh_token_repo = RefreshTokenRepository(session)
    login_attempt_repo = LoginAttemptRepository(session)
    return AuthService(
        user_repo=user_repo,
        refresh_token_repo=refresh_token_repo,
        login_attempt_repo=login_attempt_repo,
    )


async def _get_db_session():  # type: ignore[no-untyped-def]
    """Lazy wrapper for get_db_session to avoid circular imports at module level."""
    from app.infrastructure.database import get_db_session

    async for session in get_db_session():
        yield session


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Set the refresh token as an HTTP-only cookie.

    Cookie domain and secure flag are controlled via environment config.
    """
    settings = get_settings()
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
        domain=settings.COOKIE_DOMAIN or None,
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Clear the refresh token cookie."""
    settings = get_settings()
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
        domain=settings.COOKIE_DOMAIN or None,
    )


@router.post("/login", response_model=APIResponse[LoginResponse])
async def login(
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[LoginResponse]:
    """Authenticate a user with email and password.

    Returns an access token and user info in the response body,
    and sets the refresh token as an HTTP-only cookie.
    """
    auth_service = _get_auth_service(session)
    token_pair = await auth_service.login(email=body.email, password=body.password)

    # Set refresh token as HTTP-only cookie
    _set_refresh_cookie(response, token_pair.refresh_token)

    # Look up user to include in response
    user_repo = UserRepository(session)
    user = await user_repo.get_by_email(body.email)

    # Commit the session to persist login attempt and refresh token
    await session.commit()

    login_response = LoginResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        user=UserInfo.model_validate(user),
    )
    return APIResponse(
        success=True,
        data=login_response,
        message="Login successful",
    )


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[TokenResponse]:
    """Refresh the access token using the refresh token cookie.

    Rotates the refresh token and returns a new access token.
    Sets the new refresh token as an HTTP-only secure cookie.
    """
    from app.core.exceptions import UnauthorizedException

    if refresh_token is None:
        raise UnauthorizedException(message="Missing refresh token")

    auth_service = _get_auth_service(session)
    token_pair = await auth_service.refresh(refresh_token_str=refresh_token)

    # Set new rotated refresh token cookie
    _set_refresh_cookie(response, token_pair.refresh_token)

    # Commit the session to persist token rotation
    await session.commit()

    token_response = TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
    )
    return APIResponse(
        success=True,
        data=token_response,
        message="Token refreshed successfully",
    )


@router.post("/logout", response_model=APIResponse[None])
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[None]:
    """Log out the current user by invalidating the refresh token.

    Clears the refresh token cookie regardless of whether the token
    was valid or present.
    """
    if refresh_token is not None:
        auth_service = _get_auth_service(session)
        await auth_service.logout(refresh_token_str=refresh_token)
        await session.commit()

    # Always clear the refresh token cookie
    _clear_refresh_cookie(response)

    return APIResponse(
        success=True,
        data=None,
        message="Logged out successfully",
    )


from app.core.dependencies import get_current_user
from app.models.user import User


@router.get("/me", response_model=APIResponse[UserInfo])
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> APIResponse[UserInfo]:
    """Get the current authenticated user's info from the JWT token."""
    return APIResponse(
        success=True,
        data=UserInfo.model_validate(current_user),
        message="User info retrieved successfully",
    )
