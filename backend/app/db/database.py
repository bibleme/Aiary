import os
# app/db/database.py (Base를 models.py에서 가져와 사용합니다)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 🚨 models.py에서 Base를 가져옵니다.
from app.db.model import Base 

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://aiary_user:aiary_pass@127.0.0.1:5432/aiary_db"
) 

# 1. 비동기 엔진 생성
engine = create_async_engine(
    DATABASE_URL,
    echo=True, 
    connect_args={"ssl": "disable"},
)

# 2. 비동기 세션 생성기
AsyncSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine, 
    class_=AsyncSession
)

# 3. FastAPI Dependency Injection 함수 
async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session