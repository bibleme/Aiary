# app/services/cv_monthly_summary.py
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.model import (
    Diary,
    VisionImage,
    VisionPerson,
    VisionObjectInstance,
    VisionAppearance,
    VisionInteraction,
)

EMOTION_KR_MAP = {
    "happy": "기쁨/행복",
    "neutral": "평온/집중",
    "sad": "슬픔/시무룩",
    "angry": "분노/화남",
    "fear": "두려움/공포",
    "surprise": "놀람/신남",
    "disgust": "싫음/불편",
}


async def generate_cv_monthly_summary(
    db: AsyncSession,
    user_id: int,
    target_month: str,
) -> dict:
    start = datetime.strptime(target_month + "-01", "%Y-%m-%d").date()
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1, day=1)
    else:
        end = start.replace(month=start.month + 1, day=1)

    diary_rows = await db.execute(
        select(Diary.id)
        .where(Diary.user_id == user_id)
        .where(Diary.diary_date >= start)
        .where(Diary.diary_date < end)
    )
    diary_ids = [row[0] for row in diary_rows.all()]
    if not diary_ids:
        return {
            "report_month": target_month,
            "favorite_objects": [],
            "emotions_summary": [],
            "highlight_places": [],
        }

    vision_rows = await db.execute(
        select(VisionImage)
        .where(VisionImage.user_id == user_id)
        .where(VisionImage.one_line_diary_id.in_(diary_ids))
        .where(VisionImage.cv_status == "done")
    )
    vision_images = list(vision_rows.scalars().all())
    if not vision_images:
        return {
            "report_month": target_month,
            "favorite_objects": [],
            "emotions_summary": [],
            "highlight_places": [],
        }

    vision_ids = [v.id for v in vision_images]

    person_rows = await db.execute(select(VisionPerson).where(VisionPerson.vision_image_id.in_(vision_ids)))
    persons = list(person_rows.scalars().all())

    object_rows = await db.execute(select(VisionObjectInstance).where(VisionObjectInstance.vision_image_id.in_(vision_ids)))
    objects = list(object_rows.scalars().all())

    appearance_rows = await db.execute(select(VisionAppearance).where(VisionAppearance.vision_image_id.in_(vision_ids)))
    appearances = list(appearance_rows.scalars().all())

    interaction_rows = await db.execute(select(VisionInteraction).where(VisionInteraction.vision_image_id.in_(vision_ids)))
    interactions = list(interaction_rows.scalars().all())

    vision_by_id = {v.id: v for v in vision_images}
    object_by_id = {o.id: o for o in objects}
    person_by_id = {p.id: p for p in persons}

    appearance_map = defaultdict(list)
    for ap in appearances:
        appearance_map[(ap.entity_type, ap.entity_id)].append(ap)

    # favorite_objects
    object_counter = Counter()
    object_photo_map = defaultdict(set)
    object_appearances = defaultdict(list)

    for inter in interactions:
        person = person_by_id.get(inter.person_id)
        obj = object_by_id.get(inter.object_instance_id)
        if not person or not obj:
            continue
        if person.role not in {"target_child", "assumed_child"}:
            continue

        category = obj.base_category
        object_counter[category] += 1

        vimg = vision_by_id.get(inter.vision_image_id)
        if vimg:
            object_photo_map[category].add(vimg.file_name)

        for ap in appearance_map.get(("object", obj.id), []):
            vimg2 = vision_by_id.get(ap.vision_image_id)
            if vimg2:
                object_appearances[category].append(
                    {
                        "file_name": vimg2.file_name,
                        "bbox": ap.bbox or [],
                    }
                )

    favorite_objects = []
    past_object_categories = set()
    past_rows = await db.execute(
        select(VisionObjectInstance.base_category)
        .join(VisionImage, VisionImage.id == VisionObjectInstance.vision_image_id)
        .where(VisionImage.user_id == user_id)
        .where(VisionImage.year_month < target_month)
    )
    for row in past_rows.all():
        past_object_categories.add(row[0])

    for rank, (category, _) in enumerate(object_counter.most_common(3), start=1):
        favorite_objects.append(
            {
                "rank": rank,
                "category": category,
                "is_new": category not in past_object_categories,
                "photo_count": len(object_photo_map[category]),
                "appearances": object_appearances[category],
            }
        )

    # emotions_summary
    emotion_counter = Counter()
    emotion_best = {}

    candidate_persons = [p for p in persons if p.role in {"target_child", "assumed_child"} and p.emotion]
    total_emotions = len(candidate_persons)

    for p in candidate_persons:
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
        file_name = vision_by_id[best_person.vision_image_id].file_name
        ratio = round((count / total_emotions) * 100, 1) if total_emotions > 0 else 0.0
        emotions_summary.append(
            {
                "emotion_en": emotion,
                "emotion_kr": EMOTION_KR_MAP.get(emotion, emotion),
                "ratio": ratio,
                "best_cut": {
                    "file_name": file_name,
                    "confidence": float(best_person.emotion_score or 0.0),
                    "bbox": best_bbox,
                },
            }
        )

    # highlight_places
    valid_places = [
        v for v in vision_images
        if v.predicted_tag in {"Special_Outing", "Outdoor_Outing"}
    ]

    scene_groups = defaultdict(list)
    for v in valid_places:
        # 1차 버전: predicted_tag 기준 그룹
        # 나중에 scene_vector threshold clustering으로 고도화 가능
        scene_groups[v.predicted_tag].append(v.file_name)

    past_place_tags = set()
    past_place_rows = await db.execute(
        select(VisionImage.predicted_tag)
        .where(VisionImage.user_id == user_id)
        .where(VisionImage.year_month < target_month)
        .where(VisionImage.predicted_tag.in_(["Special_Outing", "Outdoor_Outing"]))
    )
    for row in past_place_rows.all():
        if row[0]:
            past_place_tags.add(row[0])

    highlight_places = []
    ranked_places = sorted(scene_groups.items(), key=lambda x: len(x[1]), reverse=True)[:3]
    for rank, (place_key, files) in enumerate(ranked_places, start=1):
        highlight_places.append(
            {
                "rank": rank,
                "is_new": place_key not in past_place_tags,
                "photo_count": len(files),
                "photos": files,
            }
        )

    return {
        "report_month": target_month,
        "favorite_objects": favorite_objects,
        "emotions_summary": emotions_summary,
        "highlight_places": highlight_places,
    }
    