# app/services/cv_monthly_summary.py
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime
from typing import Optional
import boto3
from botocore.config import Config
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.db.model import (
    Diary,
    VisionImage,
    VisionPerson,
    VisionObjectInstance,
    VisionAppearance,
    VisionInteraction,
)
EMOTION_KR_MAP = {
    "happy": "밝은 표정",
    "neutral": "차분한 표정",
    "sad": "시무룩한 표정",
    "angry": "진지한 표정",
    "fear": "낯선 표정",
    "surprise": "놀란 표정",
    "disgust": "불편한 표정",
}
PLACE_KR_MAP = {
    "Routine_Indoor": "실내 일상",
    "Outdoor_Outing": "야외 나들이",
    "Special_Outing": "특별한 외출",
    "No_Scene": "장면 미분류",
}
OBJECT_KR_MAP = {
    "teddy bear": "인형",
    "bear": "인형",
    "dog": "강아지",
    "cat": "고양이",
    "cup": "컵",
    "bottle": "물병",
    "book": "책",
    "ball": "공",
    "handbag": "가방",
    "backpack": "가방",
    "potted plant": "화분",
    "bowl": "그릇",
    "spoon": "숟가락",
    "fork": "포크",
    "toy": "장난감",
    "kite": "장난감",
    "frisbee": "장난감",
    "skateboard": "놀이기구",
    "snowboard": "놀이기구",
}
EXCLUDED_OBJECT_CATEGORIES = {
    "person",
    "chair",
    "couch",
    "bed",
    "dining table",
    "bench",
    "toilet",
    "sink",
    "tv",
    "laptop",
    "cell phone",
    "keyboard",
    "mouse",
    "remote",
    "car",
    "truck",
    "bus",
    "motorcycle",
    "bicycle",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "traffic light",
    "donut",
    "cake",
    "pizza",
    "sandwich",
    "hot dog",
    "sports ball",
}
MIN_OBJECT_CONFIDENCE = 0.45
PRESIGNED_EXPIRES_IN = 3600
def _s3_client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        endpoint_url=f"https://s3.{settings.AWS_REGION}.amazonaws.com",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "virtual"},
        ),
    )
def _build_image_url(vimg: VisionImage) -> Optional[str]:
    if not vimg:
        return None
    if vimg.image_storage == "s3" and vimg.image_key:
        try:
            return _s3_client().generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": settings.AWS_S3_BUCKET,
                    "Key": vimg.image_key,
                },
                ExpiresIn=PRESIGNED_EXPIRES_IN,
            )
        except Exception:
            return vimg.image_url
    if vimg.image_url and vimg.image_url.startswith("/"):
        return f"{settings.PUBLIC_BASE_URL.rstrip('/')}{vimg.image_url}"
    return vimg.image_url
def _photo_item(
    vimg: VisionImage,
    diary_by_id: dict[int, Diary],
    bbox: Optional[list] = None,
    confidence: Optional[float] = None,
) -> dict:
    diary = diary_by_id.get(vimg.one_line_diary_id)
    item = {
        "diary_id": vimg.one_line_diary_id,
        "vision_image_id": vimg.id,
        "date": str(diary.diary_date) if diary else None,
        "file_name": vimg.file_name,
        "image_url": _build_image_url(vimg),
    }
    if bbox is not None:
        item["bbox"] = bbox
    if confidence is not None:
        item["confidence"] = confidence
    return item
def _is_reportable_object(category: str | None) -> bool:
    if not category:
        return False
    return category not in EXCLUDED_OBJECT_CATEGORIES
def _best_object_confidence(appearances: list) -> float:
    best = 0.0
    for ap in appearances:
        try:
            conf = float(ap.confidence or 0.0)
        except Exception:
            conf = 0.0
        best = max(best, conf)
    return best
def _empty_summary(target_month: str) -> dict:
    return {
        "report_month": target_month,
        "favorite_objects": [],
        "emotions_summary": [],
        "highlight_places": [],
        "emotion_basis": {
            "description": "얼굴이 명확히 감지된 사진 기준으로 산출한 참고용 표정 분석입니다.",
            "analyzed_face_count": 0,
            "is_reference_only": True,
        },
    }
def _parse_month_range(target_month: str):
    start = datetime.strptime(target_month + "-01", "%Y-%m-%d").date()
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1, day=1)
    else:
        end = start.replace(month=start.month + 1, day=1)
    return start, end
def _category_kr(category: str) -> str:
    return OBJECT_KR_MAP.get(category, category)
def _place_label(place_key: str) -> str:
    return PLACE_KR_MAP.get(place_key, place_key)
async def generate_cv_monthly_summary(
    db: AsyncSession,
    user_id: int,
    target_month: str,
) -> dict:
    start, end = _parse_month_range(target_month)
    diary_result = await db.execute(
        select(Diary)
        .where(Diary.user_id == user_id)
        .where(Diary.diary_date >= start)
        .where(Diary.diary_date < end)
        .order_by(Diary.diary_date.asc(), Diary.id.asc())
    )
    diaries = list(diary_result.scalars().all())
    diary_ids = [d.id for d in diaries]
    diary_by_id = {d.id: d for d in diaries}
    if not diary_ids:
        return _empty_summary(target_month)
    vision_rows = await db.execute(
        select(VisionImage)
        .where(VisionImage.user_id == user_id)
        .where(VisionImage.one_line_diary_id.in_(diary_ids))
        .where(VisionImage.cv_status == "done")
    )
    vision_images = list(vision_rows.scalars().all())
    if not vision_images:
        return _empty_summary(target_month)
    vision_ids = [v.id for v in vision_images]
    vision_by_id = {v.id: v for v in vision_images}
    person_rows = await db.execute(
        select(VisionPerson).where(VisionPerson.vision_image_id.in_(vision_ids))
    )
    persons = list(person_rows.scalars().all())
    object_rows = await db.execute(
        select(VisionObjectInstance).where(VisionObjectInstance.vision_image_id.in_(vision_ids))
    )
    objects = list(object_rows.scalars().all())
    appearance_rows = await db.execute(
        select(VisionAppearance).where(VisionAppearance.vision_image_id.in_(vision_ids))
    )
    appearances = list(appearance_rows.scalars().all())
    interaction_rows = await db.execute(
        select(VisionInteraction).where(VisionInteraction.vision_image_id.in_(vision_ids))
    )
    interactions = list(interaction_rows.scalars().all())
    object_by_id = {o.id: o for o in objects}
    person_by_id = {p.id: p for p in persons}
    appearance_map = defaultdict(list)
    for ap in appearances:
        appearance_map[(ap.entity_type, ap.entity_id)].append(ap)
    object_counter = Counter()
    object_photo_items = defaultdict(dict)
    object_appearances = defaultdict(list)
    def add_object_record(category: str, obj: VisionObjectInstance):
        vimg = vision_by_id.get(obj.vision_image_id)
        if not vimg:
            return
        object_counter[category] += 1
        object_photo_items[category][vimg.file_name] = _photo_item(vimg, diary_by_id)
        for ap in appearance_map.get(("object", obj.id), []):
            vimg2 = vision_by_id.get(ap.vision_image_id)
            if vimg2:
                object_appearances[category].append(
                    _photo_item(
                        vimg=vimg2,
                        diary_by_id=diary_by_id,
                        bbox=ap.bbox or [],
                        confidence=float(ap.confidence or 0.0),
                    )
                )
    for inter in interactions:
        person = person_by_id.get(inter.person_id)
        obj = object_by_id.get(inter.object_instance_id)
        if not person or not obj:
            continue
        if person.role not in {"target_child", "assumed_child"}:
            continue
        category = obj.base_category
        if not _is_reportable_object(category):
            continue
        obj_appearances = appearance_map.get(("object", obj.id), [])
        if _best_object_confidence(obj_appearances) < MIN_OBJECT_CONFIDENCE:
            continue
        add_object_record(category, obj)
    if not object_counter:
        for obj in objects:
            category = obj.base_category
            if not _is_reportable_object(category):
                continue
            obj_appearances = appearance_map.get(("object", obj.id), [])
            if _best_object_confidence(obj_appearances) < MIN_OBJECT_CONFIDENCE:
                continue
            add_object_record(category, obj)
    past_object_categories = set()
    past_rows = await db.execute(
        select(VisionObjectInstance.base_category)
        .join(VisionImage, VisionImage.id == VisionObjectInstance.vision_image_id)
        .where(VisionImage.user_id == user_id)
        .where(VisionImage.year_month < target_month)
    )
    for row in past_rows.all():
        if row[0]:
            past_object_categories.add(row[0])
    favorite_objects = []
    for rank, (category, _) in enumerate(object_counter.most_common(3), start=1):
        photo_items = list(object_photo_items[category].values())
        favorite_objects.append(
            {
                "rank": rank,
                "category": category,
                "category_kr": _category_kr(category),
                "is_new": category not in past_object_categories,
                "photo_count": len(photo_items),
                "photos": sorted([p["file_name"] for p in photo_items]),  # 기존 호환용
                "photo_items": photo_items,  # 프론트 표시용
                "appearances": object_appearances[category][:5],
            }
        )
    child_persons = [p for p in persons if p.role == "target_child" and p.emotion]
    if not child_persons:
        child_persons = [p for p in persons if p.role == "assumed_child" and p.emotion]
    emotion_counter = Counter()
    emotion_best = {}
    total_emotions = len(child_persons)
    for p in child_persons:
        emotion_counter[p.emotion] += 1
        current_best = emotion_best.get(p.emotion)
        if current_best is None or (p.emotion_score or 0.0) > (current_best.emotion_score or 0.0):
            emotion_best[p.emotion] = p
    emotions_summary = []
    for emotion, count in emotion_counter.most_common():
        best_person = emotion_best[emotion]
        best_bbox = []
        for ap in appearance_map.get(("person", best_person.id), []):
            best_bbox = ap.bbox or []
            break
        vimg = vision_by_id.get(best_person.vision_image_id)
        if not vimg:
            continue
        ratio = round((count / total_emotions) * 100, 1) if total_emotions > 0 else 0.0
        emotions_summary.append(
            {
                "emotion_en": emotion,
                "emotion_kr": EMOTION_KR_MAP.get(emotion, emotion),
                "ratio": ratio,
                "best_cut": _photo_item(
                    vimg=vimg,
                    diary_by_id=diary_by_id,
                    bbox=best_bbox,
                    confidence=float(best_person.emotion_score or 0.0),
                ),
            }
        )
    valid_place_tags = {"Special_Outing", "Outdoor_Outing", "Routine_Indoor"}
    scene_groups = defaultdict(list)
    for v in vision_images:
        if v.predicted_tag in valid_place_tags:
            scene_groups[v.predicted_tag].append(v)
    past_place_tags = set()
    past_place_rows = await db.execute(
        select(VisionImage.predicted_tag)
        .where(VisionImage.user_id == user_id)
        .where(VisionImage.year_month < target_month)
        .where(VisionImage.predicted_tag.in_(list(valid_place_tags)))
    )
    for row in past_place_rows.all():
        if row[0]:
            past_place_tags.add(row[0])
    highlight_places = []
    ranked_places = sorted(scene_groups.items(), key=lambda x: len(x[1]), reverse=True)[:3]
    for rank, (place_key, vimgs) in enumerate(ranked_places, start=1):
        photo_items = [_photo_item(v, diary_by_id) for v in vimgs]
        highlight_places.append(
            {
                "rank": rank,
                "place_key": place_key,
                "place_label": _place_label(place_key),
                "is_new": place_key not in past_place_tags,
                "photo_count": len(photo_items),
                "photos": sorted([p["file_name"] for p in photo_items]),  # 기존 호환용
                "photo_items": photo_items,  # 프론트 표시용
            }
        )
    return {
        "report_month": target_month,
        "favorite_objects": favorite_objects,
        "emotions_summary": emotions_summary,
        "highlight_places": highlight_places,
        "emotion_basis": {
            "description": "얼굴이 명확히 감지된 사진 기준으로 산출한 참고용 표정 분석입니다.",
            "analyzed_face_count": total_emotions,
            "is_reference_only": True,
        },
    }
