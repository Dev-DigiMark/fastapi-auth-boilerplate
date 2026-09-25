from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
async def get_me(
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Return the profile of whoever owns the access token."""
    result = await db.execute(select(User).where(User.id == int(current_user["id"])))
    user = result.scalar_one_or_none()
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
async def get_all_users(
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Return every registered user.

    Any signed-in user can call this — add an admin check before production.
    """
    return await UserService.get_all_users(db=db)
