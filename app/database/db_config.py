import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Copy .env.example to .env and fill in your "
        "database connection string."
    )

engine_kwargs = {
    # Neon suspends idle computes, which leaves dead connections in the pool.
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

if DATABASE_URL.startswith("sqlite"):
    engine_kwargs = {"connect_args": {"check_same_thread": False}}

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_database():
    # Import models so their tables are registered on Base before create_all.
    from app.models import (  # noqa: F401
        otp,
        refresh_token,
        reset_token,
        user,
        user_auth,
    )

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_database()
