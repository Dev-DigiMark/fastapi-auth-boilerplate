import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_config import get_db
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    SignUpRequest,
)
from app.services.auth_service import AuthService
from app.services.google_auth_service import GoogleAuthService

router = APIRouter(prefix="/auth", tags=["Auth"])

load_dotenv()

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.post(
    "/signup",
    summary="Register a new account",
    response_description="Confirmation plus the encrypted user ID to verify with.",
    responses={
        400: {
            "description": (
                "Username, email, or phone already taken; passwords do not "
                "match; or the email domain cannot receive mail."
            )
        },
        422: {"description": "A field failed format or length validation."},
    },
)
async def signup(data: SignUpRequest, db: AsyncSession = Depends(get_db)):
    """
    Create an account and send a 6-digit verification code.

    The account starts unverified and **cannot log in** until the code is
    confirmed. Take the `user_id` from this response and post it to
    `/otp/verify` along with the code.
    """
    return await AuthService(db).signup(data)


@router.post(
    "/login",
    summary="Log in with password",
    response_description="A bearer token, or a verification prompt if unverified.",
    responses={400: {"description": "Invalid credentials."}},
)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Exchange credentials for a JWT access token.

    You may sign in with a username, email, or phone number in the single
    `username_or_email_or_phone` field.

    There are two possible success responses. A verified account receives
    `access_token`, `refresh_token`, `token_type`, and a `user` object. An
    unverified account receives no token — a fresh OTP is sent instead.
    """
    return await AuthService(db).login(
        username_or_email_or_phone=data.username_or_email_or_phone,
        password=data.password,
    )


@router.post(
    "/refresh",
    summary="Get a new access token",
    response_description="A new access token and a replacement refresh token.",
    responses={
        401: {
            "description": (
                "The refresh token is unknown, expired, or was already used. "
                "Reuse of a rotated token revokes every session for that user."
            )
        },
    },
)
async def refresh(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """
    Trade a refresh token for a fresh access token.

    Refresh tokens are rotated: the one you send is invalidated and a new one
    comes back in the response. **Store the new one**.
    """
    return await AuthService(db).refresh_access_token(data.refresh_token)


@router.post(
    "/logout",
    summary="End the current session",
    response_description="Confirmation that the session was ended.",
)
async def logout(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """
    Revoke a refresh token so it can no longer be used.

    Always returns success, even for a token that was already revoked or never
    existed. The matching access token stays valid until it expires.
    """
    return await AuthService(db).logout(data.refresh_token)


@router.get(
    "/google",
    summary="Get the Google sign-in URL",
    response_description="An object containing the URL to redirect the user to.",
)
async def google_login():
    """Build the Google OAuth consent URL."""
    return {"auth_url": GoogleAuthService.get_google_auth_url()}


@router.post(
    "/login_or_signup_with_google",
    summary="Log in or register with a Google code",
    responses={400: {"description": "The authorization code was rejected by Google."}},
)
async def login_or_signup_with_google(
    code: str = Query(
        ...,
        description="The single-use authorization code from Google's redirect.",
        examples=["4/0AeanS0b..."],
    ),
    db: AsyncSession = Depends(get_db),
):
    """Exchange a Google authorization code for tokens and start a session."""
    return await AuthService(db).login_or_signup_with_google(code)


@router.get(
    "/google/callback",
    summary="Google OAuth redirect target",
    responses={400: {"description": "The authorization code was rejected by Google."}},
)
async def google_callback(
    code: str = Query(
        ...,
        description="Authorization code appended by Google to the redirect URI.",
        examples=["4/0AeanS0b..."],
    ),
    db: AsyncSession = Depends(get_db),
):
    """Google OAuth GET callback — same work as the POST variant."""
    return await AuthService(db).login_or_signup_with_google(code)


@router.post(
    "/forgot-password",
    summary="Email a password reset link",
    responses={404: {"description": "No account exists with that email."}},
)
async def forgot_password(
    request: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
):
    """Send a reset link. The token is valid for 15 minutes and single-use."""
    return await AuthService(db).forgot_password(email=request.email)


@router.get(
    "/reset-password",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def reset_password_page(
    request: Request,
    token: str = Query("", description="Reset token from the emailed link."),
):
    """Browser-facing page that the password reset email links to."""
    return templates.TemplateResponse(
        request=request, name="reset_password.html", context={"token": token}
    )


@router.post(
    "/reset-password",
    summary="Set a new password using a reset token",
    responses={
        400: {
            "description": "Passwords do not match, or the token is invalid or expired."
        },
        404: {"description": "No authentication record found for this user."},
    },
)
async def reset_password(
    request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
):
    """Complete a password reset."""
    return await AuthService(db).reset_password(
        token=request.token,
        new_password=request.new_password,
        confirm_password=request.confirm_password,
    )
