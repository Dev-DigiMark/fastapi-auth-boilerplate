from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY")  # Use environment variable in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30000

# HTTPBearer for handling the token
bearer_scheme = HTTPBearer()

def create_access_token(data: dict):
    """Create a JWT access token with an expiration."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_access_token(token: str):
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """
    Extract and validate the user from the token.
    Expects the token in the 'Authorization' header as 'Bearer <token>'.
    """
    token = credentials.credentials  # Extract the token from the header
    try:
        payload = verify_access_token(token)
        user_id = payload.get("sub")  # 'sub' should contain the user ID
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return {"id": user_id}  # Return a dictionary with the user ID
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
