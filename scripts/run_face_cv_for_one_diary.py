import argparse

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.model import Diary, VisionImage
from app.db import crud
from app.services.cv_runner import resolve_local_image_path
from app.services.cv_face_runner import (
    get_user_child_refs,
    verify_target_child,
    analyze_faces,
)


async def process_face_cv_for_diary(diary_id: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Diary).where(Diary.id == diary_id))
        diary = result.scalar_one_or_none()

        if diary is None:
            raise ValueError(f"Diary not found: {diary_id}")

        vision_image = await crud.get_vision_image_by_diary_id(db, diary.id)
        if vision_image is None:
            raise ValueError(
                f"VisionImage not found for diary_id={diary.id}. 먼저 /cv/process 를 실행해야 합니다."
            )

        image_path = resolve_local_image_path(diary.image_url)
        if not image_path.exists():
            raise FileNotFoundError(f"이미지 파일이 존재하지 않습니다: {image_path}")

        ref_paths = get_user_child_refs(diary.user_id)
        print("REF_COUNT =", len(ref_paths))

        target_child_found, target_child_confidence = verify_target_child(image_path, ref_paths)
        print("TARGET_CHILD_FOUND =", target_child_found)
        print("TARGET_CHILD_CONFIDENCE =", target_child_confidence)

        persons = analyze_faces(image_path, target_child_found)
        print("PERSON_COUNT =", len(persons))
        print("PERSONS =", persons)

        await crud.save_face_cv_result(
            db=db,
            vision_image=vision_image,
            target_child_found=target_child_found,
            target_child_confidence=target_child_confidence,
            persons=persons,
        )

        print("FACE_CV_SAVE_OK")
        print("VISION_IMAGE_ID =", vision_image.id)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--diary-id", type=int, required=True)
    args = parser.parse_args()

    import asyncio
    asyncio.run(process_face_cv_for_diary(args.diary_id))


if __name__ == "__main__":
    main()