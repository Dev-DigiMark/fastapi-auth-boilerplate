from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserResponse
from typing import List

class UserService:
    @staticmethod
    def get_all_users(db: Session) -> List[UserResponse]:
        """
        Retrieve all users from the database.

        :param db: Database session
        :return: List of UserResponse objects
        """
        users = db.query(User).all()
        return [UserResponse.from_user(user) for user in users]
