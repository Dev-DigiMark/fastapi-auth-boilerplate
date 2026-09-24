from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.utils.email_validator import validate_email_format, validate_email_mx_records

PASSWORD_MIN_LENGTH = 8
# bcrypt cannot hash more than 72 bytes.
PASSWORD_MAX_LENGTH = 72

PASSWORD_DESCRIPTION = (
    f"{PASSWORD_MIN_LENGTH}-{PASSWORD_MAX_LENGTH} characters, and must contain "
    "at least one letter, one number, and one symbol (any character that is "
    "not a letter or digit, such as ! @ # $ % or _). Stored only as a bcrypt "
    "hash, never in plain text."
)


def validate_password_strength(password: str) -> str:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long"
        )
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"Password must be at most {PASSWORD_MAX_LENGTH} characters long"
        )
    if not any(char.isalpha() for char in password):
        raise ValueError("Password must contain at least one letter")
    if not any(char.isdigit() for char in password):
        raise ValueError("Password must contain at least one number")
    if not any(not char.isalnum() for char in password):
        raise ValueError("Password must contain at least one symbol")
    return password


class SignUpRequest(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description=(
            "Public display name. 3-50 characters. Must be unique across all "
            "accounts."
        ),
        examples=["john_doe"],
    )
    email: str = Field(
        ...,
        description=(
            "Must be unique and correctly formatted. The domain is checked for "
            "live MX records, so it has to be a real address that can receive "
            "mail. Any domain is accepted, including company and custom ones."
        ),
        examples=["john.doe@gmail.com"],
    )
    phone_number: str = Field(
        ...,
        max_length=15,
        description=(
            "Phone number in E.164 format: a leading '+', then country code, "
            "then the number, with no spaces or dashes. Maximum 15 characters. "
            "Must be unique. Required even when otp_type is 'email', and it "
            "must be valid E.164 for SMS delivery to work."
        ),
        examples=["+14155552671"],
    )
    password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        description=PASSWORD_DESCRIPTION,
        examples=["S3curePassw0rd!"],
    )
    confirm_password: str = Field(
        ...,
        description="Must match the password field exactly.",
        examples=["S3curePassw0rd!"],
    )

    @field_validator("password")
    def check_password(cls, value: str) -> str:
        return validate_password_strength(value)
    otp_type: Literal["email", "phone"] = Field(
        ...,
        description=(
            "Where to deliver the verification code. 'email' sends it to the "
            "email above, 'phone' sends an SMS to the phone number above."
        ),
        examples=["email"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "john_doe",
                "email": "john.doe@gmail.com",
                "phone_number": "+14155552671",
                "password": "S3curePassw0rd!",
                "confirm_password": "S3curePassw0rd!",
                "otp_type": "email",
            }
        }
    )

    @model_validator(mode="before")
    def validate_email(cls, values):
        email = values.get('email')
        if email:
            # Validate the email format
            if not validate_email_format(email):
                raise HTTPException(status_code=400, detail="Invalid email format.")

            # Confirm the domain can actually receive mail
            domain = email.split("@")[-1]
            validate_email_mx_records(domain)

        return values


class LoginRequest(BaseModel):
    username_or_email_or_phone: str = Field(
        ...,
        description=(
            "Any one of the three identifiers on the account: username, email, "
            "or phone number in E.164 format."
        ),
        examples=["john.doe@gmail.com"],
    )
    password: str = Field(
        ...,
        description="The account password.",
        examples=["S3curePassw0rd!"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username_or_email_or_phone": "john.doe@gmail.com",
                "password": "S3curePassw0rd!",
            }
        }
    )


class GoogleAuthCallback(BaseModel):
    code: str = Field(
        ...,
        description="The one-time authorization code returned by Google.",
        examples=["4/0AeanS0b..."],
    )


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(
        ...,
        description=(
            "Email address of the account to reset. Must belong to an existing "
            "user."
        ),
        examples=["john.doe@gmail.com"],
    )

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "john.doe@gmail.com"}}
    )

    @field_validator('email')
    def validate_email(cls, value: str):
        if not validate_email_format(value):
            raise HTTPException(status_code=400, detail="Invalid email format.")
        domain = value.split('@')[-1]
        validate_email_mx_records(domain)
        return value


class ResetPasswordRequest(BaseModel):
    token: str = Field(
        ...,
        description=(
            "The reset token from the emailed link's ?token= query parameter. "
            "Valid for 15 minutes and single-use."
        ),
        examples=["3f2a1c9e-8b7d-4e6f-a1b2-c3d4e5f60718"],
    )
    new_password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        description=PASSWORD_DESCRIPTION,
        examples=["MyN3wPassw0rd!"],
    )
    confirm_password: str = Field(
        ...,
        description="Must match new_password exactly.",
        examples=["MyN3wPassw0rd!"],
    )

    @field_validator("new_password")
    def check_password(cls, value: str) -> str:
        return validate_password_strength(value)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "3f2a1c9e-8b7d-4e6f-a1b2-c3d4e5f60718",
                "new_password": "MyN3wPassw0rd!",
                "confirm_password": "MyN3wPassw0rd!",
            }
        }
    )
