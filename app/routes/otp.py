from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_config import get_db
from app.services.otp_service import OTPService
from app.schemas.otp import OTPCreate, OTPVerify

router = APIRouter(prefix="/otp", tags=["OTP"])


@router.post(
    "/generate",
    summary="Send a new verification code",
    response_description="Confirmation with the code's expiry timestamp.",
    responses={
        400: {
            "description": (
                "Invalid user ID, or the account has no contact for that channel."
            )
        },
        404: {"description": "No account matches the supplied user ID."},
    },
)
async def generate_otp(data: OTPCreate, db: AsyncSession = Depends(get_db)):
    """
    Resend a 6-digit code to the contact details already on the account.

    The destination is always read from the stored account record.
    """
    return await OTPService(db).send_otp_to_user(
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
async def verify_otp(data: OTPVerify, db: AsyncSession = Depends(get_db)):
    """
    Verify an account with the code that was emailed or texted.

    Does **not** return a token — call `/auth/login` afterwards.
    """
    return await OTPService(db).verify_otp(
        encrypted_user_id=data.user_id, otp_code=data.otp_code
    )
