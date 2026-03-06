# app/db/database.py
import os

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Base import 유지
from app.db.model import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://aiary_user:aiary_pass@127.0.0.1:5432/aiary_db",
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

# commit 후 객체 재사용 편의를 위해 expire_on_commit=False 설정
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session
