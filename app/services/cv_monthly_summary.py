# app/services/cv_monthly_summary.py

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime

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


PLACE_KR_MAP = {
    "Routine_Indoor": "실내 일상",
    "Outdoor_Outing": "야외 나들이",
    "Special_Outing": "특별한 외출",
    "No_Scene": "장면 미분류",
}


OBJECT_KR_MAP = {
    "teddy bear": "인형",
    "dog": "강아지",
    "cat": "고양이",
    "cup": "컵",
    "bottle": "물병",
    "book": "책",
    "ball": "공",
    "handbag": "가방",
    "potted plant": "화분",
    "bowl": "그릇",
    "toy": "장난감",
}


# 월별 대표 물건에서 제외할 너무 일반적이거나 리포트 가치가 낮은 객체
EXCLUDED_OBJECT_CATEGORIES = {
    "person",
    "chair",
    "couch",
    "bed",
    "dining table",
    "tv",
    "laptop",
    "cell phone",
}


def _empty_summary(target_month: str) -> dict:
    return {
        "report_month": target_month,
        "favorite_objects": [],
        "emotions_summary": [],
        "highlight_places": [],
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

    diary_rows = await db.execute(
        select(Diary.id)
        .where(Diary.user_id == user_id)
        .where(Diary.diary_date >= start)
        .where(Diary.diary_date < end)
    )
    diary_ids = [row[0] for row in diary_rows.all()]

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

    # ------------------------------------------------------------
    # 1. favorite_objects
    # 우선순위:
    # 1) target_child/assumed_child와 interaction이 있는 object
    # 2) interaction이 부족하면 월별 object 빈도 기반 fallback
    # ------------------------------------------------------------
    object_counter = Counter()
    object_photo_map = defaultdict(set)
    object_appearances = defaultdict(list)

    # 1차: child interaction 기반
    for inter in interactions:
        person = person_by_id.get(inter.person_id)
        obj = object_by_id.get(inter.object_instance_id)

        if not person or not obj:
            continue

        if person.role not in {"target_child", "assumed_child"}:
            continue

        category = obj.base_category
        if not category or category in EXCLUDED_OBJECT_CATEGORIES:
            continue

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

    # 2차 fallback: interaction이 없거나 너무 약하면 object 자체 빈도로 대표 물건 산출
    if not object_counter:
        for obj in objects:
            category = obj.base_category

            if not category or category in EXCLUDED_OBJECT_CATEGORIES:
                continue

            object_counter[category] += 1

            vimg = vision_by_id.get(obj.vision_image_id)
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
        favorite_objects.append(
            {
                "rank": rank,
                "category": category,
                "category_kr": _category_kr(category),
                "is_new": category not in past_object_categories,
                "photo_count": len(object_photo_map[category]),
                "photos": sorted(object_photo_map[category]),
                "appearances": object_appearances[category][:5],
            }
        )

    # ------------------------------------------------------------
    # 2. emotions_summary
    # target_child가 있으면 우선 사용하고,
    # 없으면 assumed_child를 사용한다.
    # other는 월별 아이 감정 통계에서 제외한다.
    # ------------------------------------------------------------
    child_persons = [
        p for p in persons
        if p.role == "target_child" and p.emotion
    ]

    if not child_persons:
        child_persons = [
            p for p in persons
            if p.role == "assumed_child" and p.emotion
        ]

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
                "best_cut": {
                    "file_name": vimg.file_name,
                    "confidence": float(best_person.emotion_score or 0.0),
                    "bbox": best_bbox,
                },
            }
        )

    # ------------------------------------------------------------
    # 3. highlight_places
    # 장소는 얼굴 인식과 무관하게 이미지 전체 scene tag 기준으로 집계한다.
    # No_Scene은 제외한다.
    # ------------------------------------------------------------
    valid_place_tags = {"Special_Outing", "Outdoor_Outing", "Routine_Indoor"}

    scene_groups = defaultdict(list)
    for v in vision_images:
        if v.predicted_tag in valid_place_tags:
            scene_groups[v.predicted_tag].append(v.file_name)

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

    for rank, (place_key, files) in enumerate(ranked_places, start=1):
        highlight_places.append(
            {
                "rank": rank,
                "place_key": place_key,
                "place_label": _place_label(place_key),
                "is_new": place_key not in past_place_tags,
                "photo_count": len(files),
                "photos": sorted(files),
            }
        )

    return {
        "report_month": target_month,
        "favorite_objects": favorite_objects,
        "emotions_summary": emotions_summary,
        "highlight_places": highlight_places,
    }