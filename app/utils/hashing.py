import asyncio

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Hash:
    @staticmethod
    def hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    async def ahash(password: str) -> str:
        """Bcrypt is CPU-bound — keep it off the event loop."""
        return await asyncio.to_thread(Hash.hash, password)

    @staticmethod
    async def averify(plain_password: str, hashed_password: str) -> bool:
        return await asyncio.to_thread(Hash.verify, plain_password, hashed_password)
