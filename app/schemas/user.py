from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from typing import Optional

from app.utils.crypto_util import encrypt_data


class UserBase(BaseModel):
    username: str
    email: EmailStr
    phone_number: Optional[str] = None


class UserResponse(BaseModel):
    id: str = Field(
        ...,
        description=(
            "Encrypted user ID. Send this back when an endpoint asks for a "
            "user_id; the raw numeric ID is never exposed."
        ),
        examples=["gAAAAABnV2x3k9Qd1Zr8pYcT5mNwXvLbHsJfKgRtUyIoPaSdFgHjKlZxCvBnM="],
    )
    username: str = Field(..., description="Display name.", examples=["john_doe"])
    email: str = Field(..., description="Registered email address.", examples=["john.doe@gmail.com"])
    phone_number: Optional[str] = Field(
        None,
        description="Registered phone number in E.164 format, if one was given.",
        examples=["+14155552671"],
    )
    profile_picture_url: Optional[str] = Field(
        None,
        description="Avatar URL. Populated from Google for OAuth accounts.",
        examples=["https://lh3.googleusercontent.com/a/default-user"],
    )
    is_verified: bool = Field(
        ...,
        description=(
            "True once the account has passed OTP verification, or immediately "
            "for accounts created through Google. Unverified accounts cannot "
            "obtain an access token."
        ),
        examples=[True],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "gAAAAABnV2x3k9Qd1Zr8pYcT5mNwXvLbHsJfKgRtUyIoPaSdFgHjKlZxCvBnM=",
                "username": "john_doe",
                "email": "john.doe@gmail.com",
                "phone_number": "+14155552671",
                "profile_picture_url": None,
                "is_verified": True,
            }
        }
    )

    # Automatically encrypt user_id before sending the response
    @model_validator(mode="before")
    def encrypt_user_id(cls, values):
        if "id" in values:
            values["id"] = encrypt_data(values["id"])
        return values

    @classmethod
    def from_user(cls, user) -> "UserResponse":
        """Build the public view of a User row. The ID is encrypted on the way out."""
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            phone_number=user.phone_number,
            profile_picture_url=user.profile_picture_url,
            is_verified=user.is_verified,
        )
