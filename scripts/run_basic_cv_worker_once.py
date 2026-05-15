# scripts/run_basic_cv_worker_once.py
from __future__ import annotations

import argparse
import asyncio
import gc
import os
import time

from app.config import settings
from app.db.database import AsyncSessionLocal
from app.db import crud
from app.services.cv_runner import run_cv_for_diary


async def process_one_batch(limit: int) -> dict:
    summary = {
        "picked": 0,
        "done": 0,
        "failed": 0,
        "skipped": 0,
    }

    async with AsyncSessionLocal() as db:
        targets = await crud.get_next_pending_vision_images_for_worker(
            db=db,
            limit=limit,
        )

        summary["picked"] = len(targets)

        if not targets:
            print("[CV_WORKER] no pending vision images", flush=True)
            return summary

        for vision_image in targets:
            diary = await crud.get_diary_by_id(db, vision_image.one_line_diary_id)

            if diary is None:
                await crud.mark_basic_cv_failed(
                    db=db,
                    vision_image=vision_image,
                    error_message="연결된 one_line_diary가 없습니다.",
                )
                summary["failed"] += 1
                continue

            print(
                f"[CV_WORKER] start "
                f"vision_image_id={vision_image.id} "
                f"diary_id={diary.id} "
                f"user_id={diary.user_id}",
                flush=True,
            )

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

                summary["done"] += 1

                print(
                    f"[CV_WORKER] done "
                    f"vision_image_id={vision_image.id} "
                    f"diary_id={diary.id}",
                    flush=True,
                )

            except Exception as e:
                await crud.mark_basic_cv_failed(
                    db=db,
                    vision_image=vision_image,
                    error_message=str(e),
                )

                summary["failed"] += 1

                print(
                    f"[CV_WORKER] failed "
                    f"vision_image_id={vision_image.id} "
                    f"diary_id={diary.id} "
                    f"error={e}",
                    flush=True,
                )

            finally:
                gc.collect()

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit",
        type=int,
        default=int(getattr(settings, "CV_WORKER_BATCH_LIMIT", 1)),
    )
    parser.add_argument(
        "--sleep-after",
        type=int,
        default=0,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    limit = max(1, int(args.limit))

    print(
        f"[CV_WORKER] pid={os.getpid()} "
        f"limit={limit} "
        f"cv_enabled={settings.CV_ENABLED}",
        flush=True,
    )

    started = time.time()
    summary = asyncio.run(process_one_batch(limit=limit))
    elapsed = round(time.time() - started, 2)

    print(
        f"[CV_WORKER] summary={summary} elapsed={elapsed}s",
        flush=True,
    )

    if args.sleep_after > 0:
        time.sleep(args.sleep_after)


if __name__ == "__main__":
    main()