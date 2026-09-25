from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db_config import get_db
from app.schemas.user import UserResponse
from app.services.user_service import UserService
from app.models.user import User
from app.utils.jwt import get_current_user

router = APIRouter(tags=["Users"])


@router.get(
    "/users/me",
    response_model=UserResponse,
    summary="Get the signed-in user's profile",
    response_description="The profile belonging to the bearer token.",
    responses={
        401: {"description": "Missing, malformed, or expired bearer token."},
        404: {"description": "The token is valid but the account no longer exists."},
    },
)
def get_me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Return the profile of whoever owns the access token.

    Requires an `Authorization: Bearer <token>` header. Click **Authorize** at
    the top of this page and paste a token from `/auth/login` to try it.
    """
    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_user(user)


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List all users",
    response_description="Every user account.",
    responses={401: {"description": "Missing, malformed, or expired bearer token."}},
)
def get_all_users(
    current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Return every registered user.

    Requires a valid bearer token. Note that any signed-in user can call this —
    there are no roles in this boilerplate, so add an admin check before
    exposing it in production.
    """
    return UserService.get_all_users(db=db)
