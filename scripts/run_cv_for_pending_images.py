# scripts/run_cv_for_pending_images.py
import asyncio

from app.db.database import AsyncSessionLocal
from app.db import crud
from app.db.model import Diary
from app.services.cv_runner import run_cv_for_diary
from app.config import settings


async def main():
    async with AsyncSessionLocal() as db:
        pending = await crud.get_pending_vision_images(db, limit=settings.CV_BATCH_LIMIT)
        print(f"[CV] pending count = {len(pending)}")

        for vision_image in pending:
            diary = await crud.get_diary_by_id(db, vision_image.one_line_diary_id)
            if diary is None:
                await crud.mark_vision_failed(db, vision_image, "연결된 one_line_diary가 없습니다.")
                continue

            try:
                result = await run_cv_for_diary(diary)
                await crud.save_cv_result(
                    db=db,
                    vision_image=vision_image,
                    predicted_tag=result.get("predicted_tag"),
                    scene_vector=result.get("scene_vector"),
                    target_child_found=result.get("target_child_found", False),
                    target_child_confidence=result.get("target_child_confidence"),
                    persons=result.get("persons", []),
                    objects=result.get("objects", []),
                    interactions=result.get("interactions", []),
                )
                print(f"[CV] done diary_id={diary.id}")
            except Exception as e:
                await crud.mark_vision_failed(db, vision_image, str(e))
                print(f"[CV] failed diary_id={diary.id}: {e}")


if __name__ == "__main__":
    asyncio.run(main())