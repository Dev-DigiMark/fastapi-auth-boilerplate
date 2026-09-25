from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserResponse


class UserService:
    @staticmethod
    async def get_all_users(db: AsyncSession) -> List[UserResponse]:
        result = await db.execute(select(User))
        users = result.scalars().all()
        return [UserResponse.from_user(user) for user in users]
