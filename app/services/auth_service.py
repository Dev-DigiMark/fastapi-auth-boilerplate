from datetime import datetime, timedelta
import os
import uuid

from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.models.reset_token import ResetToken
from app.models.user import User
from app.models.user_auth import UserAuth
from app.schemas.user import UserResponse
from app.services.google_auth_service import GoogleAuthService
from app.services.otp_service import OTPService
from app.utils.email_util import render_email_template, send_email
from app.utils.hashing import Hash
from app.utils.jwt import create_access_token
from app.utils.crypto_util import encrypt_data
from app.utils.refresh_token import (
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)

load_dotenv()

PASSWORD_RESET_URL = os.getenv(
    "PASSWORD_RESET_URL", "http://localhost:8000/auth/reset-password"
)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _issue_refresh_token(self, user_id: int) -> str:
        raw_token, token_hash = generate_refresh_token()
        self.db.add(
            RefreshToken(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=refresh_token_expiry(),
            )
        )
        await self.db.commit()
        return raw_token

    async def _revoke_all_tokens_for_user(self, user_id: int):
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.utcnow())
        )
        await self.db.commit()

    async def _session_response(self, user: User, message: str = None) -> dict:
        """Build the payload returned whenever a new session is established."""
        response = {
            "access_token": create_access_token({"sub": str(user.id)}),
            "refresh_token": await self._issue_refresh_token(user.id),
            "token_type": "bearer",
            "user": UserResponse.from_user(user),
        }
        if message:
            response = {"message": message, **response}
        return response

    async def refresh_access_token(self, refresh_token: str):
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh_token(refresh_token)
            )
        )
        stored = result.scalar_one_or_none()

        if not stored:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        if stored.revoked_at is not None:
            await self._revoke_all_tokens_for_user(stored.user_id)
            raise HTTPException(
                status_code=401,
                detail=(
                    "Refresh token has already been used. All sessions have "
                    "been revoked; please log in again."
                ),
            )

        if stored.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Refresh token has expired")

        result = await self.db.execute(select(User).where(User.id == stored.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        stored.revoked_at = datetime.utcnow()
        await self.db.commit()

        return await self._session_response(user)

    async def logout(self, refresh_token: str):
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh_token(refresh_token)
            )
        )
        stored = result.scalar_one_or_none()
        if stored and stored.revoked_at is None:
            stored.revoked_at = datetime.utcnow()
            await self.db.commit()

        return {"message": "Logged out successfully"}

    async def signup(self, data):
        result = await self.db.execute(
            select(User).where(
                (User.email == data.email)
                | (User.username == data.username)
                | (User.phone_number == data.phone_number)
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User already exists")

        if data.password != data.confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")

        if data.otp_type not in ["email", "phone"]:
            raise HTTPException(status_code=400, detail="Invalid otp_type")

        if data.otp_type == "email" and not data.email:
            raise HTTPException(
                status_code=400, detail="Email is required for email otp_type"
            )
        elif data.otp_type == "phone" and not data.phone_number:
            raise HTTPException(
                status_code=400, detail="Phone number is required for phone otp_type"
            )

        hashed_password = await Hash.ahash(data.password)

        user = User(
            username=data.username,
            email=data.email,
            phone_number=data.phone_number if data.phone_number else None,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        user_auth = UserAuth(
            user_id=user.id,
            auth_provider="password",
            password_hash=hashed_password,
        )
        self.db.add(user_auth)
        await self.db.commit()

        otp_service = OTPService(self.db)
        contact = data.email if data.otp_type == "email" else data.phone_number
        await otp_service.generate_and_send_otp(
            user_id=user.id, contact=contact, contact_type=data.otp_type
        )

        return {
            "message": "User registered successfully. OTP sent to verify account.",
            "user_id": encrypt_data(str(user.id)),
        }

    async def login(self, username_or_email_or_phone, password):
        result = await self.db.execute(
            select(User).where(
                (User.email == username_or_email_or_phone)
                | (User.username == username_or_email_or_phone)
                | (User.phone_number == username_or_email_or_phone)
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=400, detail="Invalid credentials")

        result = await self.db.execute(
            select(UserAuth).where(
                UserAuth.user_id == user.id,
                UserAuth.auth_provider == "password",
            )
        )
        user_auth = result.scalar_one_or_none()
        if not user_auth or not await Hash.averify(password, user_auth.password_hash):
            raise HTTPException(status_code=400, detail="Invalid credentials")

        if not user.is_verified:
            otp_service = OTPService(self.db)
            contact = user.email if user.email else user.phone_number
            contact_type = "email" if user.email else "phone"

            otp_response = await otp_service.generate_and_send_otp(
                user_id=user.id, contact=contact, contact_type=contact_type
            )
            return {
                "message": (
                    "Account not verified. An OTP has been sent to your "
                    "registered contact."
                ),
                "otp_sent_to": contact,
                "expires_at": otp_response["expires_at"],
                "user_id": encrypt_data(str(user.id)),
            }

        return await self._session_response(user)

    async def login_or_signup_with_google(self, code: str):
        tokens = await GoogleAuthService.exchange_code_for_tokens(code)
        user_info = await GoogleAuthService.get_user_info(tokens["id_token"])
        email = user_info["email"]
        username = user_info.get("name", email.split("@")[0])

        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            user = User(email=email, username=username, is_verified=True)
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)

            user_auth = UserAuth(
                user_id=user.id,
                auth_provider="google",
                password_hash=None,
            )
            self.db.add(user_auth)
            await self.db.commit()

        return await self._session_response(user, message="Login successful")

    async def forgot_password(self, email: str):
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        reset_token = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        self.db.add(
            ResetToken(user_id=user.id, token=reset_token, expires_at=expires_at)
        )
        await self.db.commit()

        reset_url = f"{PASSWORD_RESET_URL}?token={reset_token}"
        email_content = render_email_template(
            "email_reset_password.html",
            reset_url=reset_url,
            valid_minutes=15,
            username=user.username,
        )
        await send_email(
            to=user.email, subject="Reset Your Password", body=email_content
        )

        return {"message": "Password reset email sent"}

    async def reset_password(self, token: str, new_password: str, confirm_password: str):
        if new_password != confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")

        result = await self.db.execute(
            select(ResetToken).where(ResetToken.token == token)
        )
        reset_token = result.scalar_one_or_none()
        if not reset_token or reset_token.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        result = await self.db.execute(
            select(UserAuth).where(UserAuth.user_id == reset_token.user_id)
        )
        user_auth = result.scalar_one_or_none()
        if not user_auth:
            raise HTTPException(
                status_code=404, detail="User authentication record not found"
            )

        user_auth.password_hash = await Hash.ahash(new_password)
        await self.db.delete(reset_token)
        await self.db.commit()

        return {"message": "Password reset successfully"}
