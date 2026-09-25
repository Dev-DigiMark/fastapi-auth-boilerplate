from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.otp import OTP
from app.models.user import User
from app.utils.otp_util import OTP_VALIDITY_MINUTES, generate_otp, otp_expiry
from app.utils.email_util import render_email_template, send_email
from app.utils.sms_util import send_sms
from app.utils.crypto_util import decrypt_data


class OTPService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_otp_to_user(self, encrypted_user_id: str, contact_type: str = "email"):
        """
        Resolve a user from their encrypted ID and send an OTP to the contact
        details already on file. The destination is never taken from the
        request, so an OTP can't be redirected to an attacker's address.
        """
        try:
            user_id = int(decrypt_data(encrypted_user_id))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid user ID")

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        contact = user.email if contact_type == "email" else user.phone_number
        if not contact:
            raise HTTPException(
                status_code=400,
                detail=f"User has no {contact_type} on record",
            )

        otp_result = await self.generate_and_send_otp(
            user_id=user_id, contact=contact, contact_type=contact_type
        )
        if "error" in otp_result:
            raise HTTPException(status_code=500, detail=otp_result["error"])
        return otp_result

    async def generate_and_send_otp(
        self, user_id: int, contact: str, contact_type: str = "email"
    ):
        if not user_id or not isinstance(user_id, int):
            return {"error": "Invalid user_id"}
        if not contact or not isinstance(contact, str):
            return {"error": "Invalid contact information"}
        if contact_type not in ["email", "phone"]:
            return {"error": "Invalid contact type"}

        otp_code = generate_otp()
        expires_at = otp_expiry()

        try:
            otp_entry = OTP(user_id=user_id, otp_code=otp_code, expires_at=expires_at)
            self.db.add(otp_entry)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            return {"error": f"Database error: {str(e)}"}

        try:
            if contact_type == "email":
                result = await self.db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                body = render_email_template(
                    "email_otp.html",
                    otp_code=otp_code,
                    valid_minutes=OTP_VALIDITY_MINUTES,
                    username=user.username if user else None,
                )
                await send_email(to=contact, subject="Your OTP Code", body=body)
            elif contact_type == "phone":
                await send_sms(
                    to=contact,
                    message=(
                        f"Your OTP code is: {otp_code}. "
                        f"It will expire in {OTP_VALIDITY_MINUTES} minutes."
                    ),
                )
        except Exception as e:
            await self.db.rollback()
            return {"error": f"Failed to send OTP: {str(e)}"}

        return {"message": "OTP sent successfully", "expires_at": expires_at}

    async def verify_otp(self, encrypted_user_id: str, otp_code: str):
        try:
            user_id = int(decrypt_data(encrypted_user_id))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid user ID")

        result = await self.db.execute(
            select(OTP).where(OTP.user_id == user_id, OTP.otp_code == otp_code)
        )
        otp_entry = result.scalar_one_or_none()

        if not otp_entry:
            raise HTTPException(status_code=400, detail="Invalid OTP")

        if otp_entry.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="OTP has expired")

        otp_entry.verified = True
        await self.db.commit()

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_verified = True
            await self.db.commit()

        return {"message": "OTP verified successfully"}
