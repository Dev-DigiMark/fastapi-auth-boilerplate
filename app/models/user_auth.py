from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database.db_config import Base

class UserAuth(Base):
    __tablename__ = "user_auth"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    auth_provider = Column(String(50), nullable=False)
    password_hash = Column(Text, nullable=True)  # Only for 'password' provider
    oauth_provider_id = Column(String(255), nullable=True)  # OAuth-specific ID
    oauth_access_token = Column(Text, nullable=True)  # Optional: Store token if needed
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="auth")
