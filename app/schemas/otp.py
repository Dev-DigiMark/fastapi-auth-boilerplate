from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from datetime import datetime

from app.utils.crypto_util import encrypt_data

ENCRYPTED_ID_DESCRIPTION = (
    "The encrypted user ID string returned by /auth/signup or by /auth/login "
    "when the account is not yet verified. Pass it back exactly as received; "
    "it is not the numeric database ID."
)

ENCRYPTED_ID_EXAMPLE = "gAAAAABnV2x3k9Qd1Zr8pYcT5mNwXvLbHsJfKgRtUyIoPaSdFgHjKlZxCvBnM="


class OTPBase(BaseModel):
    otp_code: str = Field(..., min_length=6, max_length=6)
    user_id: int
    expires_at: datetime


class OTPCreate(BaseModel):
    user_id: str = Field(
        ...,
        description=ENCRYPTED_ID_DESCRIPTION,
        examples=[ENCRYPTED_ID_EXAMPLE],
    )
    contact_type: Literal["email", "phone"] = Field(
        "email",
        description=(
            "Delivery channel for the code. The destination is read from the "
            "account on file, so 'email' uses the registered email and 'phone' "
            "uses the registered phone number. Returns 400 if the account has "
            "no value for the channel you pick."
        ),
        examples=["email"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": ENCRYPTED_ID_EXAMPLE,
                "contact_type": "email",
            }
        }
    )


class OTPVerify(BaseModel):
    otp_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description=(
            "The 6-digit numeric code from the email or SMS. Expires 5 minutes "
            "after it was generated."
        ),
        examples=["483920"],
    )
    user_id: str = Field(
        ...,
        description=ENCRYPTED_ID_DESCRIPTION,
        examples=[ENCRYPTED_ID_EXAMPLE],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "otp_code": "483920",
                "user_id": ENCRYPTED_ID_EXAMPLE,
            }
        }
    )


class OTPResponse(BaseModel):
    id: int
    otp_code: str
    user_id: str  # This will now be encrypted when sending, decrypted when receiving
    expires_at: datetime
    verified: bool

    @model_validator(mode="before")
    def encrypt_user_id(cls, values):
        if "user_id" in values:
            values["user_id"] = encrypt_data(values["user_id"])
        return values

    @field_validator("expires_at", mode="before")
    def serialize_datetime(cls, value):
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    class Config:
        from_attributes = True
