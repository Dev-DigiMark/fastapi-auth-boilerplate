from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.db_config import get_db
from app.services.otp_service import OTPService
from app.schemas.otp import OTPCreate, OTPVerify

router = APIRouter(prefix="/otp", tags=["OTP"])


@router.post(
    "/generate",
    summary="Send a new verification code",
    response_description="Confirmation with the code's expiry timestamp.",
    responses={
        400: {"description": "Invalid user ID, or the account has no contact for that channel."},
        404: {"description": "No account matches the supplied user ID."},
    },
)
def generate_otp(data: OTPCreate, db: Session = Depends(get_db)):
    """
    Resend a 6-digit code to the contact details already on the account.

    Use this when the original code from signup expired or never arrived. The
    code is valid for 5 minutes.

    The destination is always read from the stored account record and can never
    be supplied in the request, which stops a code from being redirected to
    someone else's address.
    """
    otp_service = OTPService(db)
    return otp_service.send_otp_to_user(
        encrypted_user_id=data.user_id, contact_type=data.contact_type
    )


@router.post(
    "/verify",
    summary="Confirm a verification code",
    response_description="Confirmation that the account is now verified.",
    responses={
        400: {"description": "Invalid user ID, wrong code, or the code has expired."},
    },
)
def verify_otp(data: OTPVerify, db: Session = Depends(get_db)):
    """
    Verify an account with the code that was emailed or texted to the user.

    On success the account is marked verified and can log in normally. This
    does **not** return a token — call `/auth/login` afterwards to get one.
    """
    otp_service = OTPService(db)
    return otp_service.verify_otp(encrypted_user_id=data.user_id, otp_code=data.otp_code)
