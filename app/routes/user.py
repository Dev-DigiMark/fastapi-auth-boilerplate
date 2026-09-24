from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db_config import get_db
from app.schemas.user import UserResponse
from app.services.user_service import UserService
from app.models.user import User
from app.utils.jwt import get_current_user

router = APIRouter()

# Route to get user details (requires token)
@router.get("/users/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user.id,  # This is the integer ID from the database, it will be encrypted automatically
        username=user.username,
        email=user.email,
        phone_number=user.phone_number,
        profile_picture_url=user.profile_picture_url,
        is_verified=user.is_verified,
    )

# Route to get all users (admin-only or privileged access)
@router.get("/users", response_model=List[UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    return UserService.get_all_users(db=db)
