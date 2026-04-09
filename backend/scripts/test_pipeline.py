import asyncio
import os
import json
from datetime import date
from dotenv import load_dotenv  # 🌟 .env 로드용 라이브러리 추가

# 🌟 1. .env 파일 읽어오기
load_dotenv()

# SQLAlchemy 비동기 설정 불러오기
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 작성하신 모듈들 임포트
from app.db.model import Base, User, Diary
from app.services.vision_analyzer import process_vision_analysis
from app.services.report_generator import generate_monthly_report

# 🌟 2. .env에서 DATABASE_URL 가져오기
DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    raise ValueError("❌ .env 파일에서 DATABASE_URL을 찾을 수 없습니다!")

print(f"🔗 연결할 DB 주소: {DB_URL}") 

# 비동기 엔진 생성
engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def run_test():
    # 1. DB 초기화 및 테이블 생성
    print("\n🛠️ 1. DB 테이블 초기화 중...")
    async with engine.begin() as conn:
        # 주의: 기존 test DB의 데이터가 모두 날아갑니다!
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # 2 & 3. 가짜 유저 생성 및 [폴더 내 모든 사진] 연속 분석
    print("\n👤 2 & 3. 유저 생성 및 연속 비전 AI 분석 시작...")
    
    # 🌟 사진이 들어있는 타겟 폴더 경로 설정
    target_dir = "media/images"
    if not os.path.exists(target_dir):
        target_dir = "backend/media/images" # 루트 폴더 실행 대비

    if not os.path.exists(target_dir):
        print(f"❌ 오류: '{target_dir}' 폴더를 찾을 수 없습니다.")
        return

    # 폴더 안의 이미지 파일만 긁어오기 (my_child_ref.jpg는 분석 대상에서 제외)
    valid_extensions = ('.jpg', '.jpeg', '.png')
    test_images = [
        os.path.join(target_dir, f) 
        for f in os.listdir(target_dir) 
        if f.lower().endswith(valid_extensions) and f != "my_child_ref.jpg"
    ]

    test_images.sort()

    if not test_images:
        print(f"❌ 오류: '{target_dir}' 폴더 안에 분석할 이미지 파일이 없습니다!")
        return
    else:
        print(f"📸 '{target_dir}' 폴더에서 총 {len(test_images)}장의 사진을 찾았습니다. 분석을 시작합니다!")

    async with AsyncSessionLocal() as db:
        # 유저 1명 생성
        new_user = User(email="test_bulk@test.com", hashed_password="hashed")
        db.add(new_user)
        await db.flush()
        user_id = new_user.id

        # 긁어온 사진들을 하나씩 돌면서 분석 시작!
        for idx, img_path in enumerate(test_images, start=1):
            # 해당 사진의 일기 생성 (타겟 월 2026-04)
            new_diary = Diary(
                user_id=user_id,
                content=f"자동 스캔 테스트 일기 {idx}",
                image_url=img_path,
                diary_date=date(2026, 4, 15)  
            )
            db.add(new_diary)
            await db.flush() # diary_id 발급

            # 비전 분석 파이프라인 통과
            print(f"   👉 [{idx}/{len(test_images)}] '{os.path.basename(img_path)}' 비전 분석 중...")
            await process_vision_analysis(diary_id=new_diary.id, image_path=img_path, db=db)
            print(f"   ✅ 완료!")

        # 모든 일기와 분석 결과를 최종 저장
        await db.commit()

    # 4. 리포트 생성 파이프라인 실행
    print("\n📊 4. [리포트 파이프라인] 월간 리포트 생성 시작...")
    async with AsyncSessionLocal() as db:
        report_result = await generate_monthly_report(db=db, user_id=user_id, target_month="2026-04")
        
        print("\n🎉 모든 파이프라인 성공! 최종 리포트 JSON 출력:\n")
        print(json.dumps(report_result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(run_test())