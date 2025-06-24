from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlmodel import Session


from core.database import get_db
from api.dependencies import get_current_user
from model import User
from schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from schemas.basic import MessageResponse

from services.auth_service import AuthService

from core.config import settings

router = APIRouter(tags=["Auth"])
auth_service = AuthService()


@router.post("/register", response_model=TokenResponse)
def register(
    data: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
    request: Request = None,
):
    access_token, raw_refresh_token = auth_service.register(data, db, request)

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

    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    request: Request = None,
):
    access_token, raw_refresh_token = auth_service.login(data, db, request)
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

    return TokenResponse(access_token=access_token)

@router.post("/refresh_token", response_model=TokenResponse)
def refresh_token(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    raw_refresh_token_cookie: str | None = Cookie(None, alias="refresh_token"),
):
    if not raw_refresh_token_cookie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token not provided in cookie.",
        )

    new_access_token, new_raw_refresh_token = auth_service.refresh_token(
        raw_refresh_token_cookie, db, request
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

    return TokenResponse(access_token=new_access_token)


@router.post("/logout/all", response_model=MessageResponse)
def logout_all(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return auth_service.logout_all_devices(current_user, db)


@router.post("/logout/this", response_model=MessageResponse)
def logout_this_device(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    raw_refresh_token_cookie: str | None = Cookie(None, alias="refresh_token"),
):
    if not raw_refresh_token_cookie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token not provided in cookie.",
        )
    return auth_service.logout_current_device(
        current_user, raw_refresh_token_cookie, db
    )
