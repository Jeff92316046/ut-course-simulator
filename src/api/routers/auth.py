from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlmodel import Session
import logging  # 導入 logging 模組

from core.database import get_db
from api.dependencies import get_current_user
from model import User
from schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from schemas.basic import MessageResponse

from services.auth_service import AuthService

from core.config import settings


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Auth"])
auth_service = AuthService()


@router.post("/register", response_model=TokenResponse)
def register(
    data: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
    request: Request = None,
):
    logger.info(f"Attempting to register new user with email: {data.email}")

    try:
        access_token, raw_refresh_token = auth_service.register(data, db, request)
    except HTTPException as e:
        logger.warning(f"User registration failed for email {data.email}: {e.detail}")
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during registration for email {data.email}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to an internal server error. Please try again later.",
        )

    expires_at_timestamp = (
        datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    ).timestamp()

    is_secure_cookie = settings.APP_MODE == "prod"

    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,
        secure=is_secure_cookie,
        samesite="lax",
        expires=int(expires_at_timestamp),
        path="/api/auth",
    )
    logger.info(
        f"User {data.email} registered successfully and refresh token cookie set."
    )
    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    request: Request = None,
):
    logger.info(f"Attempting to log in user with email: {data.email}")

    try:
        access_token, raw_refresh_token = auth_service.login(data, db, request)
    except HTTPException as e:
        logger.warning(f"User login failed for email {data.email}: {e.detail}")
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during login for email {data.email}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to an internal server error. Please try again later.",
        )

    expires_at_timestamp = (
        datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    ).timestamp()

    is_secure_cookie = settings.APP_MODE == "prod"

    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,
        secure=is_secure_cookie,
        samesite="lax",
        expires=int(expires_at_timestamp),
        path="/api/auth",
    )
    logger.info(
        f"User {data.email} logged in successfully and refresh token cookie set."
    )
    return TokenResponse(access_token=access_token)


@router.post("/refresh_token", response_model=TokenResponse)
def refresh_token(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    raw_refresh_token_cookie: str | None = Cookie(None, alias="refresh_token"),
):
    logger.info("Attempting to refresh access token using refresh token cookie.")

    if not raw_refresh_token_cookie:
        logger.warning(
            "Refresh token not provided in cookie for token refresh request."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token not provided in cookie.",
        )

    try:
        new_access_token, new_raw_refresh_token = auth_service.refresh_token(
            raw_refresh_token_cookie, db, request
        )
    except HTTPException as e:
        logger.warning(f"Token refresh failed: {e.detail}")
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during token refresh: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed due to an internal server error. Please try again later.",
        )

    expires_at_timestamp = (
        datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    ).timestamp()

    is_secure_cookie = settings.APP_MODE == "prod"

    response.set_cookie(
        key="refresh_token",
        value=new_raw_refresh_token,
        httponly=True,
        secure=is_secure_cookie,
        samesite="lax",
        expires=int(expires_at_timestamp),
        path="/api/auth",
    )
    logger.info("Access token refreshed successfully and new refresh token cookie set.")
    return TokenResponse(access_token=new_access_token)


@router.post("/logout/all", response_model=MessageResponse)
def logout_all(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    logger.info(f"User {current_user.id} attempting to log out from all devices.")
    try:
        result = auth_service.logout_all_devices(current_user, db)
        logger.info(f"User {current_user.id} logged out from all devices successfully.")
        return result
    except HTTPException as e:
        logger.warning(
            f"Logout all devices failed for user {current_user.id}: {e.detail}"
        )
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during logout all devices for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed due to an internal server error. Please try again later.",
        )


@router.post("/logout/this", response_model=MessageResponse)
def logout_this_device(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    raw_refresh_token_cookie: str | None = Cookie(None, alias="refresh_token"),
):
    logger.info(f"User {current_user.id} attempting to log out from current device.")
    if not raw_refresh_token_cookie:
        logger.warning(
            "Refresh token not provided in cookie for current device logout request."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token not provided in cookie.",
        )
    try:
        result = auth_service.logout_current_device(
            current_user, raw_refresh_token_cookie, db
        )
        logger.info(
            f"User {current_user.id} logged out from current device successfully."
        )
        return result
    except HTTPException as e:
        logger.warning(
            f"Logout current device failed for user {current_user.id}: {e.detail}"
        )
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during logout current device for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed due to an internal server error. Please try again later.",
        )
