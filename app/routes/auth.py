import os

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.db_config import get_db
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SignUpRequest,
)
from app.services.auth_service import AuthService
from app.services.google_auth_service import GoogleAuthService

router = APIRouter(prefix="/auth", tags=["Auth"])

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")


@router.post(
    "/signup",
    summary="Register a new account",
    response_description="Confirmation plus the encrypted user ID to verify with.",
    responses={
        400: {
            "description": (
                "Username, email, or phone already taken; passwords do not "
                "match; or the email domain is not accepted."
            )
        },
        422: {"description": "A field failed format or length validation."},
    },
)
def signup(data: SignUpRequest, db: Session = Depends(get_db)):
    """
    Create an account and send a 6-digit verification code.

    The account starts unverified and **cannot log in** until the code is
    confirmed. Take the `user_id` from this response and post it to
    `/otp/verify` along with the code.

    Note that the email must be on one of the accepted provider domains and the
    phone number must be in E.164 format (`+14155552671`) — see the field
    descriptions below.
    """
    auth_service = AuthService(db)
    return auth_service.signup(data)


@router.post(
    "/login",
    summary="Log in with password",
    response_description="A bearer token, or a verification prompt if unverified.",
    responses={
        400: {"description": "Invalid credentials."},
    },
)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """
    Exchange credentials for a JWT access token.

    You may sign in with a username, email, or phone number in the single
    `username_or_email_or_phone` field.

    There are two possible success responses. A verified account receives
    `{"access_token": ..., "token_type": "bearer"}`. An unverified account
    receives no token — a fresh OTP is sent instead and the response carries
    `user_id` and `expires_at` so you can send the user to the verify step.

    Use the token as `Authorization: Bearer <token>` on protected endpoints.
    """
    auth_service = AuthService(db)
    return auth_service.login(
        username_or_email_or_phone=data.username_or_email_or_phone,
        password=data.password,
    )


@router.get(
    "/google",
    summary="Get the Google sign-in URL",
    response_description="An object containing the URL to redirect the user to.",
)
def google_login():
    """
    Build the Google OAuth consent URL.

    Redirect the browser to the returned `auth_url`. Google sends the user back
    to your configured `GOOGLE_REDIRECT_URI` with a `code` query parameter,
    which you then pass to `/auth/google/callback`.
    """
    return {"auth_url": GoogleAuthService.get_google_auth_url()}


@router.post(
    "/login_or_signup_with_google",
    summary="Log in or register with a Google code",
    responses={400: {"description": "The authorization code was rejected by Google."}},
)
def login_or_signup_with_google(
    code: str = Query(
        ...,
        description=(
            "The single-use authorization code from Google's redirect. Expires "
            "quickly and cannot be reused."
        ),
        examples=["4/0AeanS0b..."],
    ),
    db: Session = Depends(get_db),
):
    """
    Exchange a Google authorization code for an access token.

    Creates the account on first use. Google accounts are trusted as verified,
    so they skip the OTP step entirely and get a token immediately.
    """
    auth_service = AuthService(db)
    return auth_service.login_or_signup_with_google(code, db)


@router.get(
    "/google/callback",
    summary="Google OAuth redirect target",
    responses={400: {"description": "The authorization code was rejected by Google."}},
)
def google_callback(
    code: str = Query(
        ...,
        description="Authorization code appended by Google to the redirect URI.",
        examples=["4/0AeanS0b..."],
    ),
    db: Session = Depends(get_db),
):
    """
    The URL Google redirects to after consent.

    Does the same work as `/auth/login_or_signup_with_google`; this variant
    exists because Google calls it with a GET.
    """
    auth_service = AuthService(db)
    return auth_service.login_or_signup_with_google(code, db)


@router.post(
    "/forgot-password",
    summary="Email a password reset link",
    responses={404: {"description": "No account exists with that email."}},
)
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Send a reset link to a registered email address.

    The link points at your frontend (`FRONTEND_BASE_URL`) with a `token` query
    parameter, and the token is valid for 15 minutes and single-use.
    """
    auth_service = AuthService(db)
    return auth_service.forgot_password(email=request.email)


@router.post(
    "/reset-password",
    summary="Set a new password using a reset token",
    responses={
        400: {"description": "Passwords do not match, or the token is invalid or expired."},
        404: {"description": "No authentication record found for this user."},
    },
)
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Complete a password reset.

    Takes the token from the emailed link plus the new password. The token is
    deleted on success, so each link works only once.
    """
    auth_service = AuthService(db)
    return auth_service.reset_password(
        token=request.token,
        new_password=request.new_password,
        confirm_password=request.confirm_password,
    )
