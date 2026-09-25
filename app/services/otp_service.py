from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.otp import OTP
from app.models.user import User
from app.utils.otp_util import OTP_VALIDITY_MINUTES, generate_otp, otp_expiry
from app.utils.email_util import render_email_template, send_email
from app.utils.sms_util import send_sms
from app.utils.crypto_util import decrypt_data


class OTPService:
    def __init__(self, db: Session):
        self.db = db

    def send_otp_to_user(self, encrypted_user_id: str, contact_type: str = "email"):
        """
        Resolve a user from their encrypted ID and send an OTP to the contact
        details already on file. The destination is never taken from the
        request, so an OTP can't be redirected to an attacker's address.
        """
        try:
            user_id = int(decrypt_data(encrypted_user_id))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid user ID")

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        contact = user.email if contact_type == "email" else user.phone_number
        if not contact:
            raise HTTPException(
                status_code=400,
                detail=f"User has no {contact_type} on record",
            )

        result = self.generate_and_send_otp(
            user_id=user_id, contact=contact, contact_type=contact_type
        )
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result

    def generate_and_send_otp(self, user_id: int, contact: str, contact_type: str = "email"):
        # Step 1: Validate input
        if not user_id or not isinstance(user_id, int):
            return {"error": "Invalid user_id"}
        if not contact or not isinstance(contact, str):
            return {"error": "Invalid contact information"}
        if contact_type not in ["email", "phone"]:
            return {"error": "Invalid contact type"}

        # Step 2: Generate OTP and expiry time
        otp_code = generate_otp()
        expires_at = otp_expiry()

        # Step 3: Add OTP to the database with error handling
        try:
            otp_entry = OTP(user_id=user_id, otp_code=otp_code, expires_at=expires_at)
            self.db.add(otp_entry)
            self.db.commit()
        except Exception as e:
            self.db.rollback()  # Rollback on failure
            return {"error": f"Database error: {str(e)}"}

        # Step 4: Send OTP based on contact type
        try:
            if contact_type == "email":
                user = self.db.query(User).filter(User.id == user_id).first()
                body = render_email_template(
                    "email_otp.html",
                    otp_code=otp_code,
                    valid_minutes=OTP_VALIDITY_MINUTES,
                    username=user.username if user else None,
                )
                send_email(to=contact, subject="Your OTP Code", body=body)
            elif contact_type == "phone":
                send_sms(
                    to=contact,
                    message=(
                        f"Your OTP code is: {otp_code}. "
                        f"It will expire in {OTP_VALIDITY_MINUTES} minutes."
                    ),
                )
        except Exception as e:
            # Rollback the transaction if sending OTP fails
            self.db.rollback()
            return {"error": f"Failed to send OTP: {str(e)}"}

        return {"message": "OTP sent successfully", "expires_at": expires_at}

    def verify_otp(self, encrypted_user_id: str, otp_code: str):
        try:
            user_id = int(decrypt_data(encrypted_user_id))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid user ID")

        otp_entry = self.db.query(OTP).filter(OTP.user_id == user_id, OTP.otp_code == otp_code).first()

        if not otp_entry:
            raise HTTPException(status_code=400, detail="Invalid OTP")

        if otp_entry.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="OTP has expired")

        otp_entry.verified = True
        self.db.commit()

        # Mark user as verified
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_verified = True
            self.db.commit()

        return {"message": "OTP verified successfully"}
