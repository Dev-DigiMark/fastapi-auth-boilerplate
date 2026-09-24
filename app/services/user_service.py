from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserResponse
from typing import List
from app.utils.crypto_util import encrypt_data

class UserService:
    @staticmethod
    def get_all_users(db: Session) -> List[UserResponse]:
        """
        Retrieve all users from the database.

        :param db: Database session
        :return: List of UserResponse objects
        """
        users = db.query(User).all()
        return [
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                phone_number=user.phone_number,
                profile_picture_url=user.profile_picture_url,
                is_verified=user.is_verified,
            )
            for user in users
        ]
