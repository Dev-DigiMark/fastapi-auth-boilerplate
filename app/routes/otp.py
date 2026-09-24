from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.db_config import get_db
from app.services.otp_service import OTPService
from app.schemas.otp import OTPCreate, OTPVerify

router = APIRouter(prefix="/otp", tags=["OTP"])


@router.post("/generate")
def generate_otp(data: OTPCreate, db: Session = Depends(get_db)):
    """
    Send a fresh OTP to the contact details stored on the user's account.
    """
    otp_service = OTPService(db)
    return otp_service.send_otp_to_user(
        encrypted_user_id=data.user_id, contact_type=data.contact_type
    )


@router.post("/verify")
def verify_otp(data: OTPVerify, db: Session = Depends(get_db)):
    otp_service = OTPService(db)
    return otp_service.verify_otp(encrypted_user_id=data.user_id, otp_code=data.otp_code)
