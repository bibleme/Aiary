# app/db/crud.py
from pathlib import Path
from typing import Optional, List
from datetime import date, datetime, timedelta

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.model import (
    Diary,
    VisionImage,
    VisionPerson,
    VisionObjectInstance,
    VisionAppearance,
    VisionInteraction,
)

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
    image_storage: str = "local",
    image_key: Optional[str] = None,
    image_filename: Optional[str] = None,
) -> Diary:
    diary = Diary(
        user_id=user_id,
        content=content,
        image_url=image_url,
        image_storage=image_storage,
        image_key=image_key,
        image_filename=image_filename,
        diary_date=diary_date,
    )
    db.add(diary)
    await db.commit()
    await db.refresh(diary)
    return diary


async def delete_diary(db: AsyncSession, diary_id: int, user_id: int):
    diary = await get_diary_by_id(db, diary_id)
    if diary is None:
        return None
    if diary.user_id != user_id:
        return False

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


# =========================
# CV CRUD
# =========================

async def get_vision_image_by_diary_id(db: AsyncSession, one_line_diary_id: int) -> Optional[VisionImage]:
    result = await db.execute(
        select(VisionImage).where(VisionImage.one_line_diary_id == one_line_diary_id)
    )
    return result.scalar_one_or_none()


async def get_or_create_vision_image(db: AsyncSession, diary: Diary) -> VisionImage:
    existing = await get_vision_image_by_diary_id(db, diary.id)
    if existing:
        return existing

    image_storage = getattr(diary, "image_storage", "local") or "local"
    image_key = getattr(diary, "image_key", None)
    image_filename = getattr(diary, "image_filename", None)

    if image_filename:
        file_name = image_filename
    elif image_key:
        file_name = Path(image_key).name
    else:
        file_name = diary.image_url.split("/")[-1]

    year_month = diary.diary_date.strftime("%Y-%m")

    vision_image = VisionImage(
        one_line_diary_id=diary.id,
        user_id=diary.user_id,
        file_name=file_name,
        image_url=diary.image_url,
        image_storage=image_storage,
        image_key=image_key,
        image_filename=image_filename,
        year_month=year_month,
        cv_status="pending",
        basic_cv_status="pending",
        face_cv_status="pending",
        basic_cv_attempts=0,
        face_cv_attempts=0,
    )
    db.add(vision_image)
    await db.commit()
    await db.refresh(vision_image)
    return vision_image


async def clear_vision_children(db: AsyncSession, vision_image_id: int) -> None:
    await db.execute(delete(VisionInteraction).where(VisionInteraction.vision_image_id == vision_image_id))
    await db.execute(delete(VisionAppearance).where(VisionAppearance.vision_image_id == vision_image_id))
    await db.execute(delete(VisionPerson).where(VisionPerson.vision_image_id == vision_image_id))
    await db.execute(delete(VisionObjectInstance).where(VisionObjectInstance.vision_image_id == vision_image_id))
    await db.commit()


async def save_cv_result(
    db: AsyncSession,
    vision_image: VisionImage,
    predicted_tag: Optional[str],
    scene_vector: Optional[list[float]],
    target_child_found: bool,
    target_child_confidence: Optional[float],
    persons: list[dict],
    objects: list[dict],
    interactions: list[dict],
) -> VisionImage:
    await clear_vision_children(db, vision_image.id)

    vision_image.predicted_tag = predicted_tag
    vision_image.scene_vector = scene_vector
    vision_image.target_child_found = target_child_found
    vision_image.target_child_confidence = target_child_confidence
    vision_image.cv_status = "done"
    vision_image.basic_cv_status = "done"
    vision_image.locked_at = None
    vision_image.last_error = None
    vision_image.error_message = None
    vision_image.processed_at = datetime.utcnow()

    db.add(vision_image)
    await db.flush()

    person_rows: list[VisionPerson] = []
    for p in persons:
        row = VisionPerson(
            vision_image_id=vision_image.id,
            role=p.get("role", "other"),
            emotion=p.get("emotion"),
            emotion_score=p.get("emotion_score"),
            bbox=p.get("bbox"),
            face_confidence=p.get("face_confidence"),
        )
        db.add(row)
        person_rows.append(row)

    await db.flush()

    object_rows: list[VisionObjectInstance] = []
    for o in objects:
        row = VisionObjectInstance(
            vision_image_id=vision_image.id,
            base_category=o["base_category"],
            feature_vector=o.get("feature_vector"),
            parent_assigned_name=o.get("parent_assigned_name"),
            first_seen_vision_image_id=o.get("first_seen_vision_image_id"),
        )
        db.add(row)
        object_rows.append(row)

    await db.flush()

    for idx, p in enumerate(persons):
        bbox = p.get("bbox")
        if bbox:
            db.add(
                VisionAppearance(
                    vision_image_id=vision_image.id,
                    entity_type="person",
                    entity_id=person_rows[idx].id,
                    bbox=bbox,
                    confidence=p.get("face_confidence"),
                )
            )

    for idx, o in enumerate(objects):
        bbox = o.get("bbox")
        if bbox:
            db.add(
                VisionAppearance(
                    vision_image_id=vision_image.id,
                    entity_type="object",
                    entity_id=object_rows[idx].id,
                    bbox=bbox,
                    confidence=o.get("confidence"),
                )
            )

    for it in interactions:
        person_index = it["person_index"]
        object_index = it["object_index"]
        if person_index < len(person_rows) and object_index < len(object_rows):
            db.add(
                VisionInteraction(
                    vision_image_id=vision_image.id,
                    person_id=person_rows[person_index].id,
                    object_instance_id=object_rows[object_index].id,
                    interaction_type=it.get("interaction_type"),
                    proximity_score=it.get("proximity_score"),
                )
            )

    await db.commit()
    await db.refresh(vision_image)
    return vision_image


async def mark_vision_failed(db: AsyncSession, vision_image: VisionImage, error_message: str) -> VisionImage:
    vision_image.cv_status = "failed"
    vision_image.error_message = error_message
    vision_image.processed_at = datetime.utcnow()
    db.add(vision_image)
    await db.commit()
    await db.refresh(vision_image)
    return vision_image


async def get_pending_vision_images(db: AsyncSession, limit: int = 20) -> list[VisionImage]:
    result = await db.execute(
        select(VisionImage)
        .where(VisionImage.cv_status == "pending")
        .order_by(VisionImage.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())

async def get_next_pending_vision_images_for_worker(
    db: AsyncSession,
    limit: int = 1,
    lock_timeout_minutes: int = 30,
) -> list[VisionImage]:
    cutoff = datetime.utcnow() - timedelta(minutes=lock_timeout_minutes)

    result = await db.execute(
        select(VisionImage)
        .where(
            VisionImage.cv_status.in_(["pending", "failed"]),
            VisionImage.basic_cv_attempts < 3,
        )
        .where(
            (VisionImage.locked_at.is_(None)) |
            (VisionImage.locked_at < cutoff)
        )
        .order_by(VisionImage.created_at.asc(), VisionImage.id.asc())
        .limit(limit)
    )

    rows = list(result.scalars().all())

    for row in rows:
        row.cv_status = "processing"
        row.basic_cv_status = "processing"
        row.locked_at = datetime.utcnow()
        row.last_error = None

    await db.commit()

    for row in rows:
        await db.refresh(row)

    return rows


async def mark_basic_cv_done(
    db: AsyncSession,
    vision_image: VisionImage,
) -> VisionImage:
    vision_image.cv_status = "done"
    vision_image.basic_cv_status = "done"
    vision_image.locked_at = None
    vision_image.last_error = None
    vision_image.processed_at = datetime.utcnow()

    db.add(vision_image)
    await db.commit()
    await db.refresh(vision_image)

    return vision_image


async def mark_basic_cv_failed(
    db: AsyncSession,
    vision_image: VisionImage,
    error_message: str,
) -> VisionImage:
    vision_image.cv_status = "failed"
    vision_image.basic_cv_status = "failed"
    vision_image.basic_cv_attempts = int(vision_image.basic_cv_attempts or 0) + 1
    vision_image.locked_at = None
    vision_image.last_error = error_message[:2000]
    vision_image.error_message = error_message[:2000]
    vision_image.processed_at = datetime.utcnow()

    db.add(vision_image)
    await db.commit()
    await db.refresh(vision_image)

    return vision_image


async def save_face_cv_result(
    db: AsyncSession,
    vision_image: VisionImage,
    target_child_found: bool,
    target_child_confidence: Optional[float],
    persons: list[dict],
) -> VisionImage:
    # 기존 person / interaction / person appearance만 정리
    existing_person_rows = await db.execute(
        select(VisionPerson).where(VisionPerson.vision_image_id == vision_image.id)
    )
    existing_persons = list(existing_person_rows.scalars().all())
    existing_person_ids = [p.id for p in existing_persons]

    if existing_person_ids:
        await db.execute(
            delete(VisionInteraction).where(VisionInteraction.person_id.in_(existing_person_ids))
        )
        await db.execute(
            delete(VisionAppearance)
            .where(VisionAppearance.entity_type == "person")
            .where(VisionAppearance.entity_id.in_(existing_person_ids))
        )

    await db.execute(
        delete(VisionPerson).where(VisionPerson.vision_image_id == vision_image.id)
    )
    await db.commit()

    vision_image.target_child_found = target_child_found
    vision_image.target_child_confidence = target_child_confidence
    db.add(vision_image)
    await db.flush()

    person_rows: list[VisionPerson] = []
    for p in persons:
        row = VisionPerson(
            vision_image_id=vision_image.id,
            role=p.get("role", "other"),
            emotion=p.get("emotion"),
            emotion_score=p.get("emotion_score"),
            bbox=p.get("bbox"),
            face_confidence=p.get("face_confidence"),
        )
        db.add(row)
        person_rows.append(row)

    await db.flush()

    for idx, p in enumerate(persons):
        bbox = p.get("bbox")
        if bbox:
            db.add(
                VisionAppearance(
                    vision_image_id=vision_image.id,
                    entity_type="person",
                    entity_id=person_rows[idx].id,
                    bbox=bbox,
                    confidence=p.get("face_confidence"),
                )
            )

    await db.commit()
    await db.refresh(vision_image)
    return vision_image