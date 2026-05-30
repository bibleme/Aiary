# scripts/run_face_cv_worker_once.py
from __future__ import annotations
import argparse
import asyncio
import gc
import os
import time
from sqlalchemy import select
from app.config import settings
from app.db.database import AsyncSessionLocal
from app.db.model import Diary, VisionImage
from app.db import crud
from app.services.image_resolver import resolve_image_path_for_cv, cleanup_temp_image
from app.services.cv_face_runner import (
    get_user_child_refs,
    verify_target_child,
    analyze_faces,
)
def cleanup_memory() -> None:
    gc.collect()
async def pick_pending_face_images(db, limit: int, user_id: int | None = None) -> list[VisionImage]:
    stmt = (
        select(VisionImage)
        .where(VisionImage.face_cv_status == "pending")
        .where(VisionImage.cv_status.in_(["done", "pending"]))
        .order_by(VisionImage.created_at.asc(), VisionImage.id.asc())
        .limit(limit)
    )
    if user_id is not None:
        stmt = stmt.where(VisionImage.user_id == user_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
async def process_one(db, vision_image: VisionImage) -> str:
    diary = await crud.get_diary_by_id(db, vision_image.one_line_diary_id)
    if diary is None:
        vision_image.face_cv_status = "failed"
        vision_image.last_error = "연결된 one_line_diary가 없습니다."
        db.add(vision_image)
        await db.commit()
        return "failed"
    image_path = None
    is_temp = False
    try:
        vision_image.face_cv_status = "processing"
        db.add(vision_image)
        await db.commit()
        image_path, is_temp = resolve_image_path_for_cv(
            image_url=diary.image_url,
            image_storage=getattr(diary, "image_storage", "local"),
            image_key=getattr(diary, "image_key", None),
        )
        if not image_path.exists():
            raise FileNotFoundError(f"이미지 파일이 존재하지 않습니다: {image_path}")
        ref_paths = get_user_child_refs(diary.user_id)
        print(
            f"[FACE_CV] start vision_image_id={vision_image.id} "
            f"diary_id={diary.id} user_id={diary.user_id} ref_count={len(ref_paths)}",
            flush=True,
        )
        target_child_found, target_child_confidence = verify_target_child(
            image_path=image_path,
            ref_paths=ref_paths,
        )
        persons = analyze_faces(
            image_path=image_path,
            target_child_found=target_child_found,
        )
        await crud.save_face_cv_result(
            db=db,
            vision_image=vision_image,
            target_child_found=target_child_found,
            target_child_confidence=target_child_confidence,
            persons=persons,
        )
        vision_image.face_cv_status = "done"
        vision_image.last_error = None
        db.add(vision_image)
        await db.commit()
        print(
            f"[FACE_CV] done vision_image_id={vision_image.id} "
            f"diary_id={diary.id} target_child_found={target_child_found} "
            f"person_count={len(persons)}",
            flush=True,
        )
        del persons
        return "done"
    except Exception as e:
        vision_image.face_cv_status = "failed"
        vision_image.last_error = str(e)[:1000]
        db.add(vision_image)
        await db.commit()
        print(
            f"[FACE_CV] failed vision_image_id={vision_image.id} "
            f"diary_id={getattr(diary, 'id', None)} error={e}",
            flush=True,
        )
        return "failed"
    finally:
        if image_path is not None:
            cleanup_temp_image(image_path, is_temp)
        cleanup_memory()
async def main_async(limit: int, user_id: int | None, sleep_seconds: int) -> None:
    if not settings.CV_ENABLED:
        print("[FACE_CV] CV_ENABLED=False -> exit")
        return
    started = time.time()
    print(
        f"[FACE_CV] pid={os.getpid()} limit={limit} user_id={user_id} "
        f"sleep_seconds={sleep_seconds}",
        flush=True,
    )
    summary = {"picked": 0, "done": 0, "failed": 0}
    async with AsyncSessionLocal() as db:
        items = await pick_pending_face_images(db, limit=limit, user_id=user_id)
        summary["picked"] = len(items)
        for idx, vision_image in enumerate(items, start=1):
            result = await process_one(db, vision_image)
            summary[result] = summary.get(result, 0) + 1
            if idx < len(items) and sleep_seconds > 0:
                print(f"[FACE_CV] sleep {sleep_seconds}s", flush=True)
                time.sleep(sleep_seconds)
    elapsed = round(time.time() - started, 2)
    print(f"[FACE_CV] summary={summary} elapsed={elapsed}s", flush=True)
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--user-id", type=int, default=None)
    parser.add_argument("--sleep-seconds", type=int, default=15)
    args = parser.parse_args()
    if args.limit < 1:
        raise ValueError("limit은 1 이상이어야 합니다.")
    if args.limit > 2:
        raise ValueError("t3.small에서는 face CV limit은 최대 2까지만 허용합니다.")
    asyncio.run(
        main_async(
            limit=args.limit,
            user_id=args.user_id,
            sleep_seconds=args.sleep_seconds,
        )
    )
if __name__ == "__main__":
    main()