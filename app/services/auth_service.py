from datetime import datetime, timedelta
import os
import uuid
from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy.orm import Session
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
from app.services.otp_service import OTPService

load_dotenv()

# Defaults to the reset page this API serves itself. Point it at your own
# frontend page once you have one.
PASSWORD_RESET_URL = os.getenv(
    "PASSWORD_RESET_URL", "http://localhost:8000/auth/reset-password"
)


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def _issue_refresh_token(self, user_id: int) -> str:
        raw_token, token_hash = generate_refresh_token()
        self.db.add(
            RefreshToken(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=refresh_token_expiry(),
            )
        )
        self.db.commit()
        return raw_token

    def _revoke_all_tokens_for_user(self, user_id: int):
        self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        ).update({"revoked_at": datetime.utcnow()})
        self.db.commit()

    def _session_response(self, user: User, message: str = None) -> dict:
        """Build the payload returned whenever a new session is established."""
        response = {
            "access_token": create_access_token({"sub": str(user.id)}),
            "refresh_token": self._issue_refresh_token(user.id),
            "token_type": "bearer",
            "user": UserResponse.from_user(user),
        }
        if message:
            response = {"message": message, **response}
        return response

    def refresh_access_token(self, refresh_token: str):
        """
        Exchange a refresh token for a new access token.

        The presented token is rotated away and replaced, so each one works
        exactly once.
        """
        stored = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token_hash == hash_refresh_token(refresh_token))
            .first()
        )

        if not stored:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        if stored.revoked_at is not None:
            # This token was already rotated away, so whoever just sent it is
            # replaying an old one. Treat it as theft and drop every session.
            self._revoke_all_tokens_for_user(stored.user_id)
            raise HTTPException(
                status_code=401,
                detail=(
                    "Refresh token has already been used. All sessions have "
                    "been revoked; please log in again."
                ),
            )

        if stored.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Refresh token has expired")

        user = self.db.query(User).filter(User.id == stored.user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        stored.revoked_at = datetime.utcnow()
        self.db.commit()

        return self._session_response(user)

    def logout(self, refresh_token: str):
        """
        Revoke a refresh token.

        Always reports success so the endpoint cannot be used to probe which
        tokens exist. The current access token stays valid until it expires,
        because JWTs are not checked against the database.
        """
        stored = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token_hash == hash_refresh_token(refresh_token))
            .first()
        )
        if stored and stored.revoked_at is None:
            stored.revoked_at = datetime.utcnow()
            self.db.commit()

        return {"message": "Logged out successfully"}

    def signup(self, data):
        # Check for duplicate user
        if self.db.query(User).filter(
            (User.email == data.email) |
            (User.username == data.username) |
            (User.phone_number == data.phone_number)
        ).first():
            raise HTTPException(status_code=400, detail="User already exists")

        # Validate password confirmation
        if data.password != data.confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")

        # Validate otp_type and corresponding contact
        if data.otp_type not in ["email", "phone", "both"]:
            raise HTTPException(status_code=400, detail="Invalid otp_type")

        if data.otp_type == "email" and not data.email:
            raise HTTPException(status_code=400, detail="Email is required for email otp_type")
        elif data.otp_type == "phone" and not data.phone_number:
            raise HTTPException(status_code=400, detail="Phone number is required for phone otp_type")

        # Hash the password
        hashed_password = Hash.hash(data.password)

        # Create new user


        user = User(
            username=data.username,
            email=data.email,
            phone_number=data.phone_number if data.phone_number else None
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Create user authentication entry
        user_auth = UserAuth(
            user_id=user.id,
            auth_provider="password",
            password_hash=hashed_password
        )
        self.db.add(user_auth)
        self.db.commit()

        # Generate and send OTP
        otp_service = OTPService(self.db)
        contact_type = data.otp_type
        contact = None

        if contact_type == 'email':
            contact = data.email
        elif contact_type == 'phone':
            contact = data.phone_number

        otp_service.generate_and_send_otp(user_id=user.id, contact=contact, contact_type=contact_type)

        encrypted_user_id = encrypt_data(str(user.id))

        return {
            "message": "User registered successfully. OTP sent to verify account.",
            "user_id": encrypted_user_id
        }


    def login(self, username_or_email_or_phone, password):
        user = self.db.query(User).filter(
            (User.email == username_or_email_or_phone) |
            (User.username == username_or_email_or_phone) |
            (User.phone_number == username_or_email_or_phone)
        ).first()

        if not user:
            raise HTTPException(status_code=400, detail="Invalid credentials")

        user_auth = self.db.query(UserAuth).filter(
            UserAuth.user_id == user.id,
            UserAuth.auth_provider == "password"
        ).first()
        if not user_auth or not Hash.verify(password, user_auth.password_hash):
            raise HTTPException(status_code=400, detail="Invalid credentials")


        if not user.is_verified:
            # Generate and send OTP
            otp_service = OTPService(self.db)
            contact = user.email if user.email else user.phone_number
            contact_type = "email" if user.email else "phone"

            otp_response = otp_service.generate_and_send_otp(user_id=user.id, contact=contact, contact_type=contact_type)
            encrypted_user_id = encrypt_data(str(user.id))

            # Return response indicating OTP was sent
            return {
                "message": "Account not verified. An OTP has been sent to your registered contact.",
                "otp_sent_to": contact,
                "expires_at": otp_response["expires_at"],
                "user_id":encrypted_user_id
            }

        # If verified, start a session
        return self._session_response(user)

    def login_or_signup_with_google(self, code: str, db: Session):
        # Step 1: Exchange code for tokens
        tokens = GoogleAuthService.exchange_code_for_tokens(code)

        # Step 2: Get user info from ID token
        user_info = GoogleAuthService.get_user_info(tokens["id_token"])
        email = user_info["email"]
        username = user_info.get("name", email.split("@")[0])

        # Step 3: Check if user exists
        user = db.query(User).filter(User.email == email).first()

        if not user:
            # Step 4: Register new user if not found
            user = User(email=email, username=username, is_verified=True)
            db.add(user)
            db.commit()
            db.refresh(user)

            # Add user auth details for Google login
            user_auth = UserAuth(
                user_id=user.id,
                auth_provider="google",
                password_hash=None  # No password for Google login
            )
            db.add(user_auth)
            db.commit()

        # Step 5: Start a session
        return self._session_response(user, message="Login successful")
    


    def forgot_password(self, email: str):
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Generate a reset token
        reset_token = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        # Save the token in the database
        new_reset_token = ResetToken(user_id=user.id, token=reset_token, expires_at=expires_at)
        self.db.add(new_reset_token)
        self.db.commit()

        # Send the reset email
        reset_url = f"{PASSWORD_RESET_URL}?token={reset_token}"
        email_content = render_email_template(
            "email_reset_password.html",
            reset_url=reset_url,
            valid_minutes=15,
            username=user.username,
        )
        send_email(to=user.email, subject="Reset Your Password", body=email_content)

        return {"message": "Password reset email sent"}

    def reset_password(self, token: str, new_password: str, confirm_password: str):
        # Ensure passwords match
        if new_password != confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")

        # Validate reset token
        reset_token = self.db.query(ResetToken).filter(ResetToken.token == token).first()
        if not reset_token or reset_token.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        # Find the corresponding user_auth entry
        user_auth = self.db.query(UserAuth).filter(UserAuth.user_id == reset_token.user_id).first()
        if not user_auth:
            raise HTTPException(status_code=404, detail="User authentication record not found")

        # Update the password hash
        user_auth.password_hash = Hash.hash(new_password)
        self.db.add(user_auth)
        self.db.commit()

        # Delete the reset token
        self.db.delete(reset_token)
        self.db.commit()

        return {"message": "Password reset successfully"}