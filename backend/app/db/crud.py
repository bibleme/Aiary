# backend/app/db/crud.py

from pathlib import Path
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date

from app.db.model import Diary


IMAGES_DIR = Path("media") / "images"


async def get_diary_by_id(db: AsyncSession, diary_id: int) -> Optional[Diary]:
    result = await db.execute(select(Diary).where(Diary.id == diary_id))
    return result.scalar_one_or_none()


async def list_diaries_by_user(
    db: AsyncSession,
    user_id: int,
    diary_date: Optional[date] = None,
) -> List[Diary]:
    stmt = select(Diary).where(Diary.user_id == user_id)
    if diary_date:
        stmt = stmt.where(Diary.diary_date == diary_date)
    stmt = stmt.order_by(Diary.created_at.desc())

    result = await db.execute(stmt)
    return result.scalars().all()


async def create_diary(
    db: AsyncSession,
    user_id: int,
    content: str,
    image_url: str,
    diary_date: date,
) -> Diary:
    diary = Diary(
        user_id=user_id,
        content=content,
        image_url=image_url,
        diary_date=diary_date,
    )
    db.add(diary)
    await db.commit()
    await db.refresh(diary)
    return diary


async def delete_diary(db: AsyncSession, diary_id: int, user_id: int):
    """
    return:
      - None: diary not found
      - False: not owner
      - True: deleted
    """
    diary = await get_diary_by_id(db, diary_id)
    if diary is None:
        return None
    if diary.user_id != user_id:
        return False

    # 이미지 파일 삭제 시도 (실패해도 DB 삭제는 진행)
    try:
        if diary.image_url and diary.image_url.startswith("/media/images/"):
            filename = diary.image_url.split("/")[-1]
            file_path = IMAGES_DIR / filename
            if file_path.exists():
                file_path.unlink()
    except Exception:
        pass

    await db.delete(diary)
    await db.commit()
    return True
