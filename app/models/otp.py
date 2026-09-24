from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from app.database.db_config import Base
from datetime import datetime


class OTP(Base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # Must be Integer
    otp_code = Column(String(10), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    verified = Column(Boolean, default=False)
