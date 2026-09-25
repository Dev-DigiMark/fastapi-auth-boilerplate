import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Copy .env.example to .env and fill in your "
        "database connection string."
    )


def to_async_database_url(url: str) -> str:
    """
    Convert a sync SQLAlchemy URL into an async driver URL.

    Neon pooled URLs often include sslmode= / channel_binding= which asyncpg
    does not accept — those are rewritten to ssl=require.
    """
    if "+asyncpg" in url or "+aiosqlite" in url:
        return url

    if url.startswith("sqlite"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)

    url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    url = url.replace("postgres://", "postgresql+asyncpg://", 1)

    parts = urlsplit(url)
    original_qs = parse_qsl(parts.query, keep_blank_values=True)
    had_sslmode = any(k == "sslmode" for k, _ in original_qs)
    qs = [(k, v) for k, v in original_qs if k not in ("sslmode", "channel_binding")]
    if had_sslmode or "neon.tech" in (parts.hostname or ""):
        if not any(k == "ssl" for k, _ in qs):
            qs.append(("ssl", "require"))

    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(qs), parts.fragment)
    )


ASYNC_DATABASE_URL = to_async_database_url(DATABASE_URL)

engine_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

if ASYNC_DATABASE_URL.startswith("sqlite"):
    engine_kwargs = {"connect_args": {"check_same_thread": False}}

engine = create_async_engine(ASYNC_DATABASE_URL, **engine_kwargs)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


async def create_database():
    # Import models so their tables are registered on Base before create_all.
    from app.models import (  # noqa: F401
        otp,
        refresh_token,
        reset_token,
        user,
        user_auth,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    import asyncio

    asyncio.run(create_database())
