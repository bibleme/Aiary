# scripts/run_face_cv_for_month.py
import argparse
import asyncio
import gc
import time
from datetime import datetime

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.model import Diary, VisionPerson
from app.db import crud
from app.services.cv_runner import resolve_local_image_path
from app.services.cv_face_runner import (
    get_user_child_refs,
    verify_target_child,
    analyze_faces,
)


def parse_month_range(target_month: str):
    """
    YYYY-MM 형식의 문자열을 받아
    해당 월의 시작일(start)과 다음 달 시작일(end)을 반환한다.
    예: 2026-05 -> 2026-05-01 ~ 2026-06-01
    """
    start = datetime.strptime(target_month + "-01", "%Y-%m-%d").date()
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1, day=1)
    else:
        end = start.replace(month=start.month + 1, day=1)
    return start, end


async def has_face_result(db, vision_image_id: int) -> bool:
    """
    해당 vision_image_id에 이미 face 후처리 결과(VisionPerson)가 있는지 확인한다.
    있으면 True, 없으면 False.
    cron이나 재실행 시 이미 처리한 항목을 자동 skip하기 위해 사용한다.
    """
    result = await db.execute(
        select(VisionPerson.id).where(VisionPerson.vision_image_id == vision_image_id).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def process_one_diary(db, diary: Diary):
    """
    diary 하나에 대해 face 후처리를 수행한다.

    처리 흐름:
    1. 연결된 vision_image가 있는지 확인
    2. 이미 face 결과가 있으면 skip
    3. 이미지 파일이 실제로 존재하는지 확인
    4. child refs 로드
    5. target child verify
    6. emotion analyze
    7. DB 저장
    """
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

    # 큰 객체 참조 정리 + 가비지 컬렉션 힌트
    del persons
    gc.collect()

    return "success"


async def process_month(user_id: int, target_month: str, batch_size: int, sleep_seconds: int, max_new_per_run: int):
    """
    특정 유저(user_id)의 특정 월(target_month)에 해당하는 diary들을 순차 처리한다.

    핵심 안정화 포인트:
    - batch_size: 몇 개 처리할 때마다 잠깐 쉬는지
    - sleep_seconds: 배치 사이 쉬는 시간
    - max_new_per_run: 한 번의 스크립트 실행에서 '신규 처리' 최대 개수
      -> 30장 이상 월에서도 한 번에 다 돌지 않고, 여러 cron 주기에 나눠 처리하게 만든다.
    """
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
        print(f"[INFO] batch_size={batch_size}, sleep_seconds={sleep_seconds}, max_new_per_run={max_new_per_run}")

        success_count = 0
        skip_count = 0
        fail_count = 0
        processed_since_sleep = 0

        for diary in diaries:
            # 한 번 실행에서 신규 처리 최대 개수 제한
            if success_count >= max_new_per_run:
                print(f"[STOP] 신규 처리 최대 개수({max_new_per_run}) 도달 -> 이번 실행 종료")
                break

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

            # batch_size만큼 신규 처리하면 잠깐 쉬기
            if processed_since_sleep >= batch_size:
                print(f"[PAUSE] 신규 {processed_since_sleep}개 처리 완료 -> {sleep_seconds}초 대기")
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
    parser.add_argument("--max-new-per-run", type=int, default=6)
    args = parser.parse_args()

    if args.batch_size < 1:
        raise ValueError("batch_size는 1 이상이어야 합니다.")
    if args.sleep_seconds < 0:
        raise ValueError("sleep_seconds는 0 이상이어야 합니다.")
    if args.max_new_per_run < 1:
        raise ValueError("max_new_per_run은 1 이상이어야 합니다.")

    asyncio.run(
        process_month(
            user_id=args.user_id,
            target_month=args.target_month,
            batch_size=args.batch_size,
            sleep_seconds=args.sleep_seconds,
            max_new_per_run=args.max_new_per_run,
        )
    )


if __name__ == "__main__":
    main()