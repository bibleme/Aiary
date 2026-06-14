import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# .env 파일 로드
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def check_db():
    print("🔍 DB에 저장된 [인물 / 감정] 데이터를 확인합니다...\n")
    async with AsyncSessionLocal() as db:
        # vision_persons와 vision_images를 조인해서 보기 좋게 가져오는 쿼리
        query = text("""
            SELECT p.id, img.file_name, p.role, p.emotion, p.emotion_score
            FROM vision_persons p
            JOIN vision_appearances a ON p.id = a.entity_id AND a.entity_type = 'Person'
            JOIN vision_images img ON a.image_id = img.id
        """)
        result = await db.execute(query)
        rows = result.mappings().all()

        if not rows:
            print("❌ DB에 저장된 인물 데이터가 없습니다. (사람을 못 찾았거나 분석이 안 됨)")
            return

        print(f"✅ 총 {len(rows)}명의 인물 분석 결과가 있습니다:")
        print("-" * 65)
        print(f"{'사진 파일명':<20} | {'역할(Role)':<15} | {'감정':<10} | {'점수'}")
        print("-" * 65)
        
        for row in rows:
            # 콘솔에서 보기 좋게 출력
            print(f"{row['file_name']:<20} | {row['role']:<15} | {row['emotion']:<10} | {row['emotion_score']}")
            
        print("-" * 65)

if __name__ == "__main__":
    asyncio.run(check_db())