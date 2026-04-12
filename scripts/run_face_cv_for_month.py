# scripts/run_face_cv_for_month.py
import argparse
import asyncio
import gc
import time
from datetime import datetime

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.model import Diary, VisionImage, VisionPerson
from app.db import crud
from app.services.cv_runner import resolve_local_image_path
from app.services.cv_face_runner import (
    get_user_child_refs,
    verify_target_child,
    analyze_faces,
)


def parse_month_range(target_month: str):
    start = datetime.strptime(target_month + "-01", "%Y-%m-%d").date()
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1, day=1)
    else:
        end = start.replace(month=start.month + 1, day=1)
    return start, end


async def has_face_result(db, vision_image_id: int) -> bool:
    result = await db.execute(
        select(VisionPerson.id).where(VisionPerson.vision_image_id == vision_image_id).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def process_one_diary(db, diary: Diary):
    vision_image = await crud.get_vision_image_by_diary_id(db, diary.id)
    if vision_image is None:
        print(f"[SKIP] diary_id={diary.id} -> vision_image 없음 (먼저 /cv/process 필요)")
        return "skip"

    already_done = await has_face_result(db, vision_image.id)
    if already_done:
        print(f"[SKIP] diary_id={diary.id}, vision_image_id={vision_image.id} -> face 결과 이미 존재")
        return "skip"

    image_path = resolve_local_image_path(diary.image_url)
    if not image_path.exists():
        print(f"[SKIP] diary_id={diary.id} -> 이미지 파일 없음: {image_path}")
        return "skip"

    ref_paths = get_user_child_refs(diary.user_id)
    print(f"[START] diary_id={diary.id}, vision_image_id={vision_image.id}, ref_count={len(ref_paths)}")

    target_child_found, target_child_confidence = verify_target_child(image_path, ref_paths)
    persons = analyze_faces(image_path, target_child_found)

    await crud.save_face_cv_result(
        db=db,
        vision_image=vision_image,
        target_child_found=target_child_found,
        target_child_confidence=target_child_confidence,
        persons=persons,
    )

    print(
        f"[DONE] diary_id={diary.id}, "
        f"vision_image_id={vision_image.id}, "
        f"target_child_found={target_child_found}, "
        f"person_count={len(persons)}"
    )

    # 메모리 정리 힌트
    del persons
    gc.collect()

    return "success"


async def process_month(user_id: int, target_month: str, batch_size: int, sleep_seconds: int):
    start, end = parse_month_range(target_month)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Diary)
            .where(Diary.user_id == user_id)
            .where(Diary.diary_date >= start)
            .where(Diary.diary_date < end)
            .order_by(Diary.diary_date.asc(), Diary.id.asc())
        )
        diaries = list(result.scalars().all())

        print(f"[INFO] user_id={user_id}, target_month={target_month}, diary_count={len(diaries)}")
        print(f"[INFO] batch_size={batch_size}, sleep_seconds={sleep_seconds}")

        success_count = 0
        skip_count = 0
        fail_count = 0
        processed_since_sleep = 0

        for diary in diaries:
            try:
                result_code = await process_one_diary(db, diary)

                if result_code == "success":
                    success_count += 1
                    processed_since_sleep += 1
                elif result_code == "skip":
                    skip_count += 1
                else:
                    fail_count += 1

            except Exception as e:
                fail_count += 1
                print(f"[FAIL] diary_id={diary.id} -> {e}")

            # 소배치 후 쉬기
            if processed_since_sleep >= batch_size:
                print(f"[PAUSE] {processed_since_sleep}개 처리 완료 -> {sleep_seconds}초 대기")
                gc.collect()
                time.sleep(sleep_seconds)
                processed_since_sleep = 0

        print("----- SUMMARY -----")
        print(f"user_id={user_id}")
        print(f"target_month={target_month}")
        print(f"success_count={success_count}")
        print(f"skip_count={skip_count}")
        print(f"fail_count={fail_count}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--target-month", type=str, required=True)
    parser.add_argument("--batch-size", type=int, default=3)
    parser.add_argument("--sleep-seconds", type=int, default=20)
    args = parser.parse_args()

    if args.batch_size < 1:
        raise ValueError("batch_size는 1 이상이어야 합니다.")
    if args.sleep_seconds < 0:
        raise ValueError("sleep_seconds는 0 이상이어야 합니다.")

    asyncio.run(
        process_month(
            user_id=args.user_id,
            target_month=args.target_month,
            batch_size=args.batch_size,
            sleep_seconds=args.sleep_seconds,
        )
    )


if __name__ == "__main__":
    main()