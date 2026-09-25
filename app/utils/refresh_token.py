import hashlib
import os
import secrets
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))


def hash_refresh_token(token: str) -> str:
    """
    Hash a refresh token for storage and lookup.

    Plain SHA-256 is the right tool here rather than bcrypt: the token is 48
    bytes of random data, so there is nothing to brute force, and the hash has
    to be deterministic to be searchable.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def generate_refresh_token() -> tuple[str, str]:
    """Return a new (raw token, hash) pair. Only the raw token goes to the client."""
    raw_token = secrets.token_urlsafe(48)
    return raw_token, hash_refresh_token(raw_token)


def refresh_token_expiry() -> datetime:
    return datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
