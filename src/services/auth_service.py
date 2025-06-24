from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status, Request
from sqlmodel import Session, select

from model import User
from model import RefreshToken
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from schemas.auth import LoginRequest, RegisterRequest
from core.config import settings


class AuthService:
    def register(
        self, data: RegisterRequest, db: Session, request: Request
    ) -> tuple[str, str]:
        existing_user = db.exec(select(User).where(User.email == data.email)).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            name=data.name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        return self._issue_tokens(user, db, request)

    def login(
        self, data: LoginRequest, db: Session, request: Request
    ) -> tuple[str, str]:
        user = db.exec(select(User).where(User.email == data.email)).first()
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        return self._issue_tokens(user, db, request)

    def logout_all_devices(self, current_user: User, db: Session):
        refresh_tokens = db.exec(
            select(RefreshToken).where(
                RefreshToken.user_id == current_user.id, RefreshToken.revoked == False
            )
        ).all()

        if not refresh_tokens:
            return {"message": "No active sessions found for this user."}

        for token in refresh_tokens:
            token.revoked = True
            token.last_used_at = datetime.now(tz=timezone.utc)
            db.add(token)

        db.commit()
        return {"message": "Logged out from all devices successfully."}

    def logout_current_device(
        self, current_user: User, raw_refresh_token: str, db: Session
    ):
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == current_user.id, RefreshToken.revoked == False
        )
        possible_tokens = db.exec(stmt).all()

        found_and_revoked = False
        for token_record in possible_tokens:
            if verify_refresh_token(raw_refresh_token, token_record.hashed_token):
                token_record.revoked = True
                token_record.last_used_at = datetime.now(tz=timezone.utc)
                db.add(token_record)
                db.commit()
                found_and_revoked = True
                break

        if not found_and_revoked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active refresh token not found or already revoked.",
            )

        return {"message": "Logged out from current device successfully."}

    def refresh_token(
        self, raw_refresh_token: str, db: Session, request: Request
    ) -> tuple[str, str]:
        if not raw_refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not provided.",
            )

        stmt = select(RefreshToken).where(
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.now(tz=timezone.utc),
        )
        possible_tokens = db.exec(stmt).all()

        found_token_record = None
        for token_record in possible_tokens:
            if verify_refresh_token(raw_refresh_token, token_record.hashed_token):
                found_token_record = token_record
                break

        if not found_token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, expired, or revoked refresh token.",
            )

        user = db.exec(
            select(User).where(User.id == found_token_record.user_id)
        ).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User associated with token is inactive or not found.",
            )

        found_token_record.revoked = True
        found_token_record.last_used_at = datetime.now(tz=timezone.utc)
        db.add(found_token_record)
        db.commit()

        return self._issue_tokens(user, db, request)

    def _issue_tokens(
        self, user: User, db: Session, request: Request
    ) -> tuple[str, str]:
        payload = {"sub": str(user.id)}
        access_token = create_access_token(payload)
        raw_refresh_token, hashed_refresh_token = create_refresh_token()

        refresh_token = RefreshToken(
            user_id=user.id,
            hashed_token=hashed_refresh_token,
            user_agent=request.headers.get("User-Agent"),
            ip_address=request.client.host,
            created_at=datetime.now(tz=timezone.utc),
            expires_at=datetime.now(tz=timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        db.add(refresh_token)
        db.commit()

        return access_token, raw_refresh_token
