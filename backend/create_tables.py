# create_tables.py (최종본)

import asyncio
# database에서 engine과 Base를 임포트합니다.
from app.db.database import engine, Base 
# models를 임포트하면 이미 Base에 모든 테이블이 등록됩니다.
from app.db.model import User, Diary 


async def create_db_and_tables():
    # 🚨 테이블이 정상적으로 로드되었는지 확인합니다. (디버그 코드)
    print(f"DEBUG: Base 메타데이터에 등록된 테이블 수: {len(Base.metadata.tables)}")
    if not Base.metadata.tables:
        print("FATAL ERROR: 테이블이 메모리에 로드되지 않았습니다. import 구조를 확인하세요.")
        return 

    async with engine.begin() as conn:
        print("새로운 테이블 생성 시작 (DDL 실행)...")
        # Base에 등록된 모든 모델을 기반으로 테이블을 생성합니다.
        await conn.run_sync(Base.metadata.create_all)
        print("테이블 생성 완료!")

if __name__ == "__main__":
    asyncio.run(create_db_and_tables())