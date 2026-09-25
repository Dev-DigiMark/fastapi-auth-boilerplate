import random
import string
from datetime import datetime, timedelta

# Keep this in sync with the copy in email_otp.html / SMS messages.
OTP_VALIDITY_MINUTES = 5


def generate_otp(length=6) -> str:
    """Generate a numeric OTP of specified length."""
    return "".join(random.choices(string.digits, k=length))


def otp_expiry(minutes: int = OTP_VALIDITY_MINUTES) -> datetime:
    """Return the expiry time for the OTP."""
    return datetime.utcnow() + timedelta(minutes=minutes)
