from datetime import datetime, timedelta, timezone
import logging

from fastapi import HTTPException, status, Request
from sqlmodel import Session, select

from model import User, RefreshToken
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from schemas.auth import LoginRequest, RegisterRequest
from core.config import settings


logger = logging.getLogger(__name__)


class AuthService:
    def register(
        self, data: RegisterRequest, db: Session, request: Request
    ) -> tuple[str, str]:
        logger.debug(f"Checking if user {data.email} already exists.")
        existing_user = db.exec(select(User).where(User.email == data.email)).first()
        if existing_user:
            logger.warning(
                f"Registration failed - Email '{data.email}' is already registered."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        try:
            user = User(
                email=data.email,
                hashed_password=hash_password(data.password),
                name=data.name,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(
                f"User {user.id} ({user.email}) successfully registered and persisted."
            )
            return self._issue_tokens(user, db, request)
        except Exception as e:
            db.rollback()
            logger.error(
                f"Failed to register and persist user {data.email}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed due to an internal error.",
            )

    def login(
        self, data: LoginRequest, db: Session, request: Request
    ) -> tuple[str, str]:
        logger.debug(f"Attempting to authenticate user {data.email}.")
        user = db.exec(select(User).where(User.email == data.email)).first()
        if not user:
            logger.warning(f"Login attempt for {data.email} failed - User not found.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        if not verify_password(data.password, user.hashed_password):
            logger.warning(
                f"Login attempt for {data.email} failed - Incorrect password."
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        logger.info(f"User {user.id} ({user.email}) successfully authenticated.")
        try:
            return self._issue_tokens(user, db, request)
        except Exception as e:
            logger.error(
                f"Unexpected error during token issuance for user {user.id} after successful authentication: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login failed due to an internal error during token creation.",
            )

    def logout_all_devices(self, current_user: User, db: Session):
        logger.info(f"User {current_user.id} requested logout from all devices.")
        refresh_tokens = db.exec(
            select(RefreshToken).where(
                RefreshToken.user_id == current_user.id, RefreshToken.revoked == False
            )
        ).all()

        if not refresh_tokens:
            logger.debug(
                f"No active sessions found for user {current_user.id} to revoke."
            )
            return {"message": "No active sessions found for this user."}

        try:
            revoked_count = 0
            for token in refresh_tokens:
                token.revoked = True
                token.last_used_at = datetime.now(tz=timezone.utc)
                db.add(token)
                revoked_count += 1
            db.commit()
            logger.info(
                f"Successfully revoked {revoked_count} refresh tokens for user {current_user.id} (all devices)."
            )
            return {"message": "Logged out from all devices successfully."}
        except Exception as e:
            db.rollback()
            logger.error(
                f"Error revoking all refresh tokens for user {current_user.id}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to log out from all devices due to an internal error.",
            )

    def logout_current_device(
        self, current_user: User, raw_refresh_token: str, db: Session
    ):
        logger.info(f"User {current_user.id} requested logout from current device.")

        # Only query for potentially matching tokens to avoid unnecessary broad scans
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == current_user.id, RefreshToken.revoked == False
        )
        possible_tokens = db.exec(stmt).all()

        found_and_revoked = False
        try:
            for token_record in possible_tokens:
                if verify_refresh_token(raw_refresh_token, token_record.hashed_token):
                    token_record.revoked = True
                    token_record.last_used_at = datetime.now(tz=timezone.utc)
                    db.add(token_record)
                    db.commit()
                    found_and_revoked = True
                    logger.info(
                        f"Refresh token ID {token_record.id} successfully revoked for user {current_user.id} (current device)."
                    )
                    break
        except Exception as e:
            db.rollback()
            logger.error(
                f"Unexpected error during current device logout for user {current_user.id}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to log out current device due to an internal error.",
            )

        if not found_and_revoked:
            logger.warning(
                f"Current device logout failed for user {current_user.id} - Token not active or already revoked."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active refresh token not found or already revoked.",
            )

        return {"message": "Logged out from current device successfully."}

    def refresh_token(
        self, raw_refresh_token: str, db: Session, request: Request
    ) -> tuple[str, str]:
        logger.info("Attempting to refresh access token using a refresh token.")
        if not raw_refresh_token:
            logger.warning("Refresh token was not provided.")
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
        try:
            for token_record in possible_tokens:
                if verify_refresh_token(raw_refresh_token, token_record.hashed_token):
                    found_token_record = token_record
                    break
        except Exception as e:
            logger.error(
                f"Unexpected error during refresh token verification: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token refresh failed due to an internal error during verification.",
            )

        if not found_token_record:
            logger.warning("Refresh token not found, or it's expired/revoked/invalid.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, expired, or revoked refresh token.",
            )

        user = db.exec(
            select(User).where(User.id == found_token_record.user_id)
        ).first()
        if not user or not user.is_active:
            try:
                found_token_record.revoked = True
                found_token_record.last_used_at = datetime.now(tz=timezone.utc)
                db.add(found_token_record)
                db.commit()
                logger.warning(
                    f"Revoked refresh token ID {found_token_record.id} as associated user {found_token_record.user_id} is inactive or not found."
                )
            except Exception as e:
                db.rollback()
                logger.error(
                    f"Error revoking token {found_token_record.id} for inactive/not found user {found_token_record.user_id}: {e}",
                    exc_info=True,
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User associated with token is inactive or not found.",
            )

        try:
            found_token_record.revoked = True
            found_token_record.last_used_at = datetime.now(tz=timezone.utc)
            db.add(found_token_record)
            db.commit()
            logger.info(
                f"Successfully revoked old refresh token ID {found_token_record.id} for user {user.id}."
            )
            return self._issue_tokens(user, db, request)
        except Exception as e:
            db.rollback()
            logger.error(
                f"Failed to revoke old token or issue new ones for user {user.id}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token refresh failed due to an internal error.",
            )

    def _issue_tokens(
        self, user: User, db: Session, request: Request
    ) -> tuple[str, str]:
        logger.debug(f"Issuing new access and refresh tokens for user ID {user.id}.")
        payload = {"sub": str(user.id)}
        access_token = create_access_token(payload)
        raw_refresh_token, hashed_refresh_token = create_refresh_token()

        try:
            refresh_token = RefreshToken(
                user_id=user.id,
                hashed_token=hashed_refresh_token,
                user_agent=request.headers.get("User-Agent"),
                ip_address=request.client.host if request.client else "N/A",
                created_at=datetime.now(tz=timezone.utc),
                expires_at=datetime.now(tz=timezone.utc)
                + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            )

            db.add(refresh_token)
            db.commit()
            db.refresh(refresh_token)
            logger.info(
                f"New refresh token (ID: {refresh_token.id}) successfully created and persisted for user {user.id}."
            )
            return access_token, raw_refresh_token
        except Exception as e:
            db.rollback()
            logger.error(
                f"Failed to create and persist new refresh token for user {user.id}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to issue tokens due to a database error.",
            )
