from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from core.config import settings
from core.database import get_db
from schemas.auth import LoginRequest, TokenResponse
from services.auth_service import AuthService

oauth_router = APIRouter(tags=["OAuth2 Auth"])
auth_service = AuthService()


@oauth_router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    access_token, raw_refresh_token = auth_service.login(
        LoginRequest(email=form_data.username, password=form_data.password), db, request
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

    return TokenResponse(access_token=access_token)
