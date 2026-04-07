#app/services/monthly_report_generator.py
import hashlib
import json
from collections import Counter
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.model import Diary, MonthlyReport


def _parse_target_month(target_month: str) -> tuple[date, date]:
    if len(target_month) != 7 or target_month[4] != "-":
        raise ValueError("target_month는 YYYY-MM 형식이어야 합니다.")

    year = int(target_month[:4])
    month = int(target_month[5:7])

    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    return start_date, end_date


async def _fetch_month_diaries(
    db: AsyncSession,
    user_id: int,
    target_month: str,
) -> list[Diary]:
    start_date, end_date = _parse_target_month(target_month)

    result = await db.execute(
        select(Diary)
        .where(
            Diary.user_id == user_id,
            Diary.diary_date >= start_date,
            Diary.diary_date < end_date,
        )
        .order_by(Diary.diary_date.asc(), Diary.created_at.asc(), Diary.id.asc())
    )
    return list(result.scalars().all())


def _compute_source_hash(diaries: list[Diary]) -> str:
    hasher = hashlib.sha256()
    for d in diaries:
        hasher.update(
            f"{d.id}|{d.diary_date}|{d.created_at.isoformat()}|{d.content}|{d.image_url}".encode("utf-8")
        )
    return hasher.hexdigest()


def _load_scene_cache(user_id: int, target_month: str) -> dict[int, dict]:
    path = settings.MONTHLY_REPORT_SCENE_CACHE_PATH
    if not path:
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

    if not isinstance(raw, list):
        return {}

    scene_map: dict[int, dict] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue

        if str(item.get("user_id")) != str(user_id):
            continue

        item_date = str(item.get("date", ""))
        if not item_date.startswith(target_month):
            continue

        diary_id = item.get("diary_id")
        if diary_id is None:
            continue

        scene_map[int(diary_id)] = item
    return scene_map


def _build_photo_ref(diary: Diary) -> dict:
    return {
        "diary_id": diary.id,
        "date": str(diary.diary_date),
        "image_url": diary.image_url,
        "full_image_url": f"http://3.35.185.251:8000{diary.image_url}" if diary.image_url else None,
        "content": diary.content,
    }


def _normalize_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []
    return []


def _build_keywords_from_scene(scene: dict, diary: Diary) -> list[dict]:
    keywords: list[dict] = []

    action_label = scene.get("action_label")
    if action_label:
        keywords.append(
            {
                "keyword": str(action_label),
                "keyword_type": "action",
                "dates": [str(diary.diary_date)],
                "photo_count": 1,
                "photos": [_build_photo_ref(diary)],
            }
        )

    for obj in _normalize_list(scene.get("objects")):
        keywords.append(
            {
                "keyword": obj,
                "keyword_type": "object",
                "dates": [str(diary.diary_date)],
                "photo_count": 1,
                "photos": [_build_photo_ref(diary)],
            }
        )

    for place in _normalize_list(scene.get("places")):
        keywords.append(
            {
                "keyword": place,
                "keyword_type": "place",
                "dates": [str(diary.diary_date)],
                "photo_count": 1,
                "photos": [_build_photo_ref(diary)],
            }
        )

    for companion in _normalize_list(scene.get("companions")):
        keywords.append(
            {
                "keyword": companion,
                "keyword_type": "companion",
                "dates": [str(diary.diary_date)],
                "photo_count": 1,
                "photos": [_build_photo_ref(diary)],
            }
        )

    return keywords


def _build_highlights(diaries: list[Diary], scene_map: dict[int, dict]) -> list[dict]:
    scored = []

    for diary in diaries:
        scene = scene_map.get(diary.id, {})
        confidence = float(scene.get("confidence", 0) or 0)
        keywords = _build_keywords_from_scene(scene, diary)

        score = confidence
        score += len(keywords) * 0.5
        score += min(len(diary.content or ""), 40) / 40

        scored.append((score, diary, scene, keywords))

    scored.sort(key=lambda x: (x[0], x[1].created_at), reverse=True)
    top_items = scored[:3]

    highlights = []
    for _, diary, scene, keywords in top_items:
        photo_ref = _build_photo_ref(diary)
        highlights.append(
            {
                "date": str(diary.diary_date),
                "text": diary.content,
                "raw_text": diary.content,
                "source_diary_id": diary.id,
                "source_image_url": diary.image_url,
                "source_full_image_url": photo_ref["full_image_url"],
                "keywords": keywords,
                "annotations": [
                    {
                        "start": None,
                        "end": None,
                        "keyword": kw.get("keyword"),
                        "keyword_type": kw.get("keyword_type"),
                        "dates": kw.get("dates", []),
                        "photo_count": kw.get("photo_count"),
                        "photos": kw.get("photos", []),
                    }
                    for kw in keywords
                ],
                "fallback_photos": [photo_ref],
            }
        )
    return highlights


def _build_summary_strings(diaries: list[Diary], scene_map: dict[int, dict], target_month: str) -> dict:
    diary_count = len(diaries)

    object_counter = Counter()
    place_counter = Counter()
    companion_counter = Counter()

    for diary in diaries:
        scene = scene_map.get(diary.id, {})
        object_counter.update(_normalize_list(scene.get("objects")))
        place_counter.update(_normalize_list(scene.get("places")))
        companion_counter.update(_normalize_list(scene.get("companions")))

    top_objects = [name for name, _ in object_counter.most_common(3)]
    top_places = [name for name, _ in place_counter.most_common(3)]
    top_companions = [name for name, _ in companion_counter.most_common(3)]

    top_object_str = ", ".join(top_objects) if top_objects else "기록된 대표 물건이 아직 없고"
    top_place_str = ", ".join(top_places) if top_places else "특정 장소 분류는 아직 부족하고"
    top_companion_str = ", ".join(top_companions) if top_companions else "함께한 대상 정보는 아직 충분하지 않아요"

    month_overview = (
        f"{target_month}에는 총 {diary_count}개의 순간이 기록되었어요. "
        f"이번 달 기록에서는 {top_object_str} 자주 등장했어요."
    )

    pattern_summary = (
        f"반복해서 보이는 장면을 보면 {top_place_str} 중심의 기록이 많았고, "
        f"{top_companion_str}."
    )

    change_summary = (
        f"{target_month}의 기록은 날짜가 쌓일수록 더 다양한 장면과 감정이 드러나는 흐름을 보여줘요."
    )

    parent_note = (
        "이번 달 기록을 바탕으로 아이가 어떤 순간에 더 반응하고 즐거워했는지 함께 돌아보면 좋아요."
    )

    one_line_summary = (
        f"{target_month}은(는) 소소한 일상 속 반복되는 즐거움과 관계의 순간들이 차곡차곡 쌓인 한 달이었어요."
    )

    return {
        "month_overview": month_overview,
        "pattern_summary": pattern_summary,
        "change_summary": change_summary,
        "parent_note": parent_note,
        "one_line_summary": one_line_summary,
    }


async def generate_monthly_report_payload(
    db: AsyncSession,
    user_id: int,
    target_month: str,
) -> tuple[dict, dict]:
    diaries = await _fetch_month_diaries(db, user_id, target_month)

    if len(diaries) < int(settings.MONTHLY_REPORT_MIN_DIARIES):
        raise ValueError(
            f"월별 리포트를 생성하려면 한줄일기가 최소 {settings.MONTHLY_REPORT_MIN_DIARIES}개 필요합니다."
        )

    scene_map = _load_scene_cache(user_id, target_month)

    highlights = _build_highlights(diaries, scene_map)
    summaries = _build_summary_strings(diaries, scene_map, target_month)

    photo_library = [_build_photo_ref(d) for d in diaries]

    payload = {
        "user_id": user_id,
        "month": target_month,
        "mode": "text_first_with_optional_scene_cache",
        "month_overview": summaries["month_overview"],
        "pattern_summary": summaries["pattern_summary"],
        "change_summary": summaries["change_summary"],
        "parent_note": summaries["parent_note"],
        "one_line_summary": summaries["one_line_summary"],
        "highlights": highlights,
        "keyword_annotations": {},
        "keyword_photo_index": {},
        "photo_library": photo_library,
        "generated_at": datetime.utcnow().isoformat(),
    }

    snapshot = {
        "source_diary_count": len(diaries),
        "last_source_created_at": diaries[-1].created_at if diaries else None,
        "source_hash": _compute_source_hash(diaries),
    }

    return payload, snapshot


async def get_monthly_report_status(
    db: AsyncSession,
    user_id: int,
    target_month: str,
) -> dict:
    diaries = await _fetch_month_diaries(db, user_id, target_month)
    current_count = len(diaries)
    current_hash = _compute_source_hash(diaries) if diaries else ""
    last_created = diaries[-1].created_at if diaries else None

    result = await db.execute(
        select(MonthlyReport).where(
            MonthlyReport.user_id == user_id,
            MonthlyReport.target_month == target_month,
        )
    )
    stored = result.scalar_one_or_none()

    if not stored:
        return {
            "user_id": user_id,
            "month": target_month,
            "exists": False,
            "is_up_to_date": False,
            "source_diary_count": current_count,
            "stored_source_diary_count": None,
            "generated_at": None,
            "updated_at": None,
            "reason": "stored report not found",
        }

    is_up_to_date = (
        stored.source_diary_count == current_count
        and stored.source_hash == current_hash
    )

    return {
        "user_id": user_id,
        "month": target_month,
        "exists": True,
        "is_up_to_date": is_up_to_date,
        "source_diary_count": current_count,
        "stored_source_diary_count": stored.source_diary_count,
        "generated_at": stored.created_at,
        "updated_at": stored.updated_at,
        "reason": None if is_up_to_date else "source data changed",
    }


async def generate_and_store_monthly_report(
    db: AsyncSession,
    user_id: int,
    target_month: str,
) -> dict:
    payload, snapshot = await generate_monthly_report_payload(db, user_id, target_month)

    result = await db.execute(
        select(MonthlyReport).where(
            MonthlyReport.user_id == user_id,
            MonthlyReport.target_month == target_month,
        )
    )
    stored = result.scalar_one_or_none()

    if stored:
        stored.report_json = payload
        stored.source_diary_count = snapshot["source_diary_count"]
        stored.source_hash = snapshot["source_hash"]
        stored.last_source_created_at = snapshot["last_source_created_at"]
        stored.generation_version = "report_v4_server_v1"
    else:
        stored = MonthlyReport(
            user_id=user_id,
            target_month=target_month,
            report_json=payload,
            source_diary_count=snapshot["source_diary_count"],
            source_hash=snapshot["source_hash"],
            last_source_created_at=snapshot["last_source_created_at"],
            generation_version="report_v4_server_v1",
        )
        db.add(stored)

    await db.commit()
    await db.refresh(stored)

    return stored.report_json