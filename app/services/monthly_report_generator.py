#app/services/monthly_report_generator.py
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.model import Diary, MonthlyReport


INVALID_CONTENT_PATTERNS = [
    r"이미지가 제대로 보이지 않아",
    r"다시 한 번 이미지 업로드",
    r"일기를 작성하기 어려워요",
]

EMOTION_PATTERNS = [
    r"행복", r"기분", r"마음", r"포근", r"설레", r"웃음", r"사랑"
]

LOW_INFO_PATTERNS = [
    r"오늘", r"하루", r"순간", r"시간", r"가득", r"작은"
]

PLACE_LEXICON = {
    "차 안": "차 안",
    "차": "차 안",
    "자동차": "차 안",
    "집": "집",
    "공원": "공원",
    "놀이터": "놀이터",
    "식당": "식당",
    "눈밭": "눈밭",
}

COMPANION_LEXICON = {
    "아빠": "아빠",
    "엄마": "엄마",
    "친구": "친구",
    "가족": "가족",
    "선생님": "선생님",
    "형제": "형제",
}

OBJECT_LEXICON = {
    "간식": "간식",
    "과자": "간식",
    "쿠키": "간식",
    "고기": "고기",
    "불꽃": "불꽃",
    "장난감": "장난감",
    "총": "장난감 총",
    "블록": "블록",
    "책": "책",
    "곰인형": "곰인형",
    "인형": "인형",
    "눈": "눈",
    "썰매": "썰매",
}

ACTION_RULES = [
    (r"(먹|간식|과자|쿠키|한 끼)", "snack_eating", "간식/먹기", "식사/간식"),
    (r"(고기|굽)", "meal_time", "식사 시간", "식사/간식"),
    (r"(손 꼭 잡|손 잡)", "hold_hands", "손 잡기", "가족상호작용"),
    (r"(장난감|모험|놀이)", "play_time", "놀이", "놀이"),
    (r"(블록)", "block_play", "블록 놀이", "만들기"),
    (r"(책|읽)", "reading", "책 읽기", "기관생활"),
    (r"(눈|썰매)", "snow_play", "눈 놀이", "바깥활동"),
    (r"(걷|산책)", "walk", "산책", "바깥활동"),
    (r"(안|안아|품에)", "hugging", "안아주기", "가족상호작용"),
]

FREE_KEYWORD_STOPWORDS = {
    "행복", "행복한", "따뜻한", "작은", "달콤한", "가득", "가득한", "시간",
    "마음", "오늘", "하루", "정말", "반한", "포근해져요", "피었어요"
}


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def build_full_image_url(image_url: Optional[str]) -> Optional[str]:
    if not image_url:
        return None
    image_url = str(image_url).strip()
    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url
    return f"{settings.PUBLIC_BASE_URL}{image_url}"


def split_sentences(text: str) -> List[str]:
    text = str(text).strip()
    if not text:
        return []
    sents = re.split(r"(?<=[.!?다요])\s+", text)
    return [s.strip() for s in sents if s.strip()]


def soft_clean_sentence(sent: str) -> str:
    s = sent
    for p in EMOTION_PATTERNS:
        s = re.sub(p, " ", s)
    for p in LOW_INFO_PATTERNS:
        s = re.sub(p, " ", s)
    s = re.sub(r"[\"'“”‘’]", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" ,.")
    return normalize_whitespace(s)


def preprocess_diary(text: str) -> Dict[str, Any]:
    original_sents = split_sentences(text)
    cleaned_sents = []
    for sent in original_sents:
        cleaned = soft_clean_sentence(sent)
        if len(cleaned) >= 2:
            cleaned_sents.append(cleaned)
    return {
        "original_sentences": original_sents,
        "cleaned_sentences": cleaned_sents
    }


def detect_places(text: str) -> List[str]:
    return sorted({label for token, label in PLACE_LEXICON.items() if token in text})


def detect_companions(text: str) -> List[str]:
    return sorted({label for token, label in COMPANION_LEXICON.items() if token in text})


def detect_objects(text: str) -> List[str]:
    return sorted({label for token, label in OBJECT_LEXICON.items() if token in text})


def detect_actions(text: str) -> List[Dict[str, str]]:
    found = []
    for pattern, canonical, label, category in ACTION_RULES:
        if re.search(pattern, text):
            found.append({
                "raw_action": pattern,
                "canonical_action": canonical,
                "action_label": label,
                "category": category
            })
    unique = {}
    for item in found:
        unique[item["canonical_action"]] = item
    return list(unique.values())


def extract_free_keywords(text: str) -> List[str]:
    cleaned = re.sub(r"[\U00010000-\U0010ffff]", " ", text)
    cleaned = re.sub(r"[^\w\s가-힣]", " ", cleaned)
    cleaned = normalize_whitespace(cleaned)
    tokens = re.findall(r"[가-힣]{2,}", cleaned)
    out = []
    for token in tokens:
        if token in FREE_KEYWORD_STOPWORDS:
            continue
        out.append(token)
    return sorted(set(out))


def build_keyword_bundle(
    action_label: str,
    places: List[str],
    objects: List[str],
    companions: List[str],
    free_keywords: List[str]
) -> Dict[str, Any]:
    keyword_types = {}
    ordered_keywords = []

    def add_keyword(keyword: str, keyword_type: str) -> None:
        if not keyword:
            return
        keyword = str(keyword).strip()
        if not keyword:
            return
        if keyword not in ordered_keywords:
            ordered_keywords.append(keyword)
        if keyword not in keyword_types or keyword_types[keyword] == "free":
            keyword_types[keyword] = keyword_type

    add_keyword(action_label, "action")
    for item in places:
        add_keyword(item, "place")
    for item in objects:
        add_keyword(item, "object")
    for item in companions:
        add_keyword(item, "companion")
    for item in free_keywords[:5]:
        add_keyword(item, "free")

    return {
        "photo_keywords": ordered_keywords,
        "photo_keyword_types": keyword_types
    }


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


async def _fetch_month_diaries(db: AsyncSession, user_id: int, target_month: str) -> list[Diary]:
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
    diaries = list(result.scalars().all())

    filtered = []
    for diary in diaries:
        content = normalize_whitespace(diary.content or "")
        if not content:
            continue
        if any(re.search(pattern, content) for pattern in INVALID_CONTENT_PATTERNS):
            continue
        diary.content = content
        filtered.append(diary)
    return filtered


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

    scene_map = {}
    for item in raw if isinstance(raw, list) else []:
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

        # normalize list fields like notebook
        for col in ["places", "objects", "companions", "photo_keywords"]:
            if col in item and isinstance(item[col], list):
                item[col] = sorted(set([str(v).strip() for v in item[col] if str(v).strip()]))

        scene_map[int(diary_id)] = item
    return scene_map


def _build_photo_ref(diary: Diary) -> dict:
    return {
        "diary_id": diary.id,
        "date": str(diary.diary_date),
        "image_url": diary.image_url,
        "full_image_url": build_full_image_url(diary.image_url),
        "content": diary.content,
    }


def rule_based_scene_extract_row(diary: Diary, target_month: str) -> List[Dict[str, Any]]:
    prep = preprocess_diary(diary.content)
    scenes = []

    source_texts = prep["cleaned_sentences"] or [diary.content]

    for sent in source_texts:
        actions = detect_actions(sent)
        places = detect_places(sent)
        companions = detect_companions(sent)
        objects = detect_objects(sent)

        if not actions and not places and not objects and not companions:
            actions = [{
                "raw_action": "",
                "canonical_action": "one_line_scene",
                "action_label": "한줄 기록",
                "category": "기타"
            }]

        free_keywords = extract_free_keywords(sent)

        for action in actions:
            keyword_bundle = build_keyword_bundle(
                action["action_label"],
                places,
                objects,
                companions,
                free_keywords,
            )
            scenes.append({
                "user_id": diary.user_id,
                "diary_id": diary.id,
                "date": str(diary.diary_date),
                "month": target_month,
                "created_at": diary.created_at.isoformat(),
                "raw_text": sent,
                "content": diary.content,
                "canonical_action": action["canonical_action"],
                "action_label": action["action_label"],
                "category": action["category"],
                "places": places,
                "objects": objects,
                "companions": companions,
                "confidence": 0.45,
                "source_image_url": diary.image_url,
                "source_full_image_url": build_full_image_url(diary.image_url),
                "photo_keywords": keyword_bundle["photo_keywords"],
                "photo_keyword_types": keyword_bundle["photo_keyword_types"],
            })

    dedup = {}
    for sc in scenes:
        key = (
            sc["diary_id"],
            sc["date"],
            sc["canonical_action"],
            tuple(sc["places"]),
            tuple(sc["objects"]),
            tuple(sc["companions"]),
        )
        if key not in dedup:
            dedup[key] = sc

    return list(dedup.values())


def _get_scenes_for_month(diaries: list[Diary], target_month: str, scene_map: dict[int, dict]) -> list[dict]:
    all_scenes = []

    for diary in diaries:
        cached = scene_map.get(diary.id)
        if cached:
            all_scenes.append(cached)
        else:
            all_scenes.extend(rule_based_scene_extract_row(diary, target_month))

    return all_scenes


def _group_synonyms(items: list[str]) -> list[list[str]]:
    # notebook의 완전한 synonym grouping 코드를 아직 서버에 그대로 옮기지 못했으므로
    # 지금은 동일 문자열 기준 최소 그룹화
    counter = Counter([x for x in items if x])
    groups = []
    for item, _ in counter.most_common():
        groups.append([item])
    return groups


def _build_keyword_photo_index(scenes: list[dict]) -> dict[str, dict]:
    index = {}
    for sc in scenes:
        photo = {
            "diary_id": sc["diary_id"],
            "date": sc["date"],
            "image_url": sc["source_image_url"],
            "full_image_url": sc["source_full_image_url"],
            "content": sc["content"],
        }
        for kw in sc.get("photo_keywords", []):
            if kw not in index:
                index[kw] = {
                    "keyword": kw,
                    "keyword_type": sc.get("photo_keyword_types", {}).get(kw, "free"),
                    "dates": [],
                    "photo_count": 0,
                    "photos": [],
                }
            index[kw]["dates"].append(sc["date"])
            index[kw]["photo_count"] += 1
            index[kw]["photos"].append(photo)

    for item in index.values():
        item["dates"] = sorted(set(item["dates"]))
        seen = set()
        uniq = []
        for p in item["photos"]:
            if p["diary_id"] not in seen:
                seen.add(p["diary_id"])
                uniq.append(p)
        item["photos"] = uniq

    return index


def _compute_monthly_stats(scenes: list[dict]) -> dict:
    action_counter = Counter()
    object_counter = Counter()
    place_counter = Counter()
    companion_counter = Counter()

    for sc in scenes:
        semantic_action = sc.get("semantic_action", sc.get("action_label"))
        if semantic_action:
            action_counter[semantic_action] += 1
        object_counter.update(sc.get("objects", []))
        place_counter.update(sc.get("places", []))
        companion_counter.update(sc.get("companions", []))

    action_groups = _group_synonyms(list(action_counter.elements()))
    keyword_groups = _group_synonyms(
        list(object_counter.elements()) + list(place_counter.elements()) + list(companion_counter.elements())
    )

    keyword_photo_index = _build_keyword_photo_index(scenes)

    return {
        "top_actions": action_counter.most_common(10),
        "top_objects": object_counter.most_common(10),
        "top_places": place_counter.most_common(10),
        "top_companions": companion_counter.most_common(10),
        "new_actions": [k for k, v in action_counter.items() if v == 1],
        "action_synonym_groups": action_groups,
        "keyword_synonym_groups": keyword_groups,
        "keyword_photo_index": keyword_photo_index,
        "raw_scenes": scenes,
    }


def score_scene(scene: dict, month_stat: Dict[str, Any]) -> Dict[str, float]:
    top_actions = dict(month_stat["top_actions"])
    top_companions = dict(month_stat["top_companions"])
    new_actions = set(month_stat["new_actions"])

    semantic_action = scene.get("semantic_action", scene["action_label"])
    representativeness = top_actions.get(semantic_action, 0)
    novelty = 2.0 if semantic_action in new_actions else 0.0
    specificity = len(scene["places"]) + len(scene["companions"]) + len(scene["objects"])
    family_signal = sum(top_companions.get(c, 0) for c in scene["companions"])
    scene_confidence = float(scene.get("confidence", 0.5))

    total = (
        1.5 * representativeness +
        2.0 * novelty +
        1.2 * specificity +
        0.8 * family_signal +
        1.0 * scene_confidence
    )
    return {
        "representativeness": representativeness,
        "novelty": novelty,
        "specificity": specificity,
        "family_signal": family_signal,
        "scene_confidence": scene_confidence,
        "total": total
    }


def _select_highlights(month_stat: Dict[str, Any], top_k: int = 3) -> list[dict]:
    scenes = month_stat["raw_scenes"]

    enriched = []
    for sc in scenes:
        scores = score_scene(sc, month_stat)
        row = {**sc, **scores}
        row["semantic_action"] = row.get("semantic_action", row["action_label"])
        row["highlight_text"] = (
            f"{row['date']}: {row['action_label']} | 대표군={row['semantic_action']} | "
            f"장소={', '.join(row['places']) if row['places'] else '-'} | "
            f"대상={', '.join(row['objects']) if row['objects'] else '-'} | "
            f"함께한 사람={', '.join(row['companions']) if row['companions'] else '-'}"
        )
        enriched.append(row)

    enriched.sort(
        key=lambda r: (r["total"], r["specificity"], r["representativeness"], r["scene_confidence"]),
        reverse=True
    )

    selected = []
    seen_semantic_actions = set()
    for row in enriched:
        semantic_action = row.get("semantic_action", row["action_label"])
        if semantic_action in seen_semantic_actions:
            continue
        selected.append(row)
        seen_semantic_actions.add(semantic_action)
        if len(selected) >= top_k:
            break

    if len(selected) < top_k:
        for row in enriched:
            if row in selected:
                continue
            selected.append(row)
            if len(selected) >= top_k:
                break

    return selected


def annotate_text(text: str, keyword_photo_index: dict) -> list[dict]:
    annotations = []
    if not text:
        return annotations

    for keyword, payload in keyword_photo_index.items():
        for m in re.finditer(re.escape(keyword), text):
            annotations.append({
                "start": m.start(),
                "end": m.end(),
                "keyword": payload["keyword"],
                "keyword_type": payload["keyword_type"],
                "dates": payload["dates"],
                "photo_count": payload["photo_count"],
                "photos": payload["photos"],
            })

    annotations.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
    return annotations


def make_rule_based_month_report(target_month: str, month_stat: Dict[str, Any], highlights: list[dict]) -> dict:
    top_actions = [x[0] for x in month_stat["top_actions"][:3]]
    top_objects = [x[0] for x in month_stat["top_objects"][:3]]
    top_places = [x[0] for x in month_stat["top_places"][:3]]
    top_companions = [x[0] for x in month_stat["top_companions"][:3]]

    action_text = ", ".join(top_actions) if top_actions else "다양한 일상 장면"
    object_text = ", ".join(top_objects) if top_objects else "대표 사물 정보가 아직 많지 않고"
    place_text = ", ".join(top_places) if top_places else "특정 장소 패턴은 아직 뚜렷하지 않고"
    companion_text = ", ".join(top_companions) if top_companions else "함께한 대상 정보는 제한적이며"

    report = {
        "month": target_month,
        "mode": "rule",
        "month_overview": f"{target_month}에는 {action_text} 중심의 기록이 차곡차곡 쌓였어요.",
        "pattern_summary": f"{place_text}, {object_text} 자주 보였어요.",
        "change_summary": "기록을 따라가면 아이가 경험한 장면이 조금씩 넓어지고 있음을 확인할 수 있어요.",
        "parent_note": f"이번 달에는 {companion_text} 아이에게 익숙하고 의미 있는 상호작용이 반복되었어요.",
        "one_line_summary": f"{target_month}은(는) {action_text}의 순간들이 돋보인 한 달이었어요.",
        "highlights": [],
    }

    for row in highlights:
        date_photos = [{
            "diary_id": row["diary_id"],
            "date": row["date"],
            "image_url": row["source_image_url"],
            "full_image_url": row["source_full_image_url"],
            "content": row["content"],
        }]

        keywords = []
        for keyword in [
            row.get("semantic_action", row["action_label"]),
            row["action_label"],
            *row["places"],
            *row["objects"],
            *row["companions"],
        ]:
            if keyword and keyword in month_stat["keyword_photo_index"]:
                keywords.append(month_stat["keyword_photo_index"][keyword])

        dedup_keywords = {}
        for payload in keywords:
            dedup_keywords[payload["keyword"]] = payload

        highlight_text = row["highlight_text"]

        report["highlights"].append({
            "date": row["date"],
            "text": highlight_text,
            "raw_text": row["raw_text"],
            "action_label": row["action_label"],
            "semantic_action": row.get("semantic_action", row["action_label"]),
            "source_diary_id": row["diary_id"],
            "source_image_url": row["source_image_url"],
            "source_full_image_url": row["source_full_image_url"],
            "keywords": list(dedup_keywords.values()),
            "annotations": annotate_text(highlight_text, {k: v for k, v in dedup_keywords.items()}),
            "fallback_photos": date_photos,
        })

    report["keyword_annotations"] = {
        field: annotate_text(report[field], month_stat["keyword_photo_index"])
        for field in ["month_overview", "pattern_summary", "change_summary", "parent_note", "one_line_summary"]
    }
    report["keyword_photo_index"] = month_stat["keyword_photo_index"]
    report["action_synonym_groups"] = month_stat.get("action_synonym_groups", [])
    report["keyword_synonym_groups"] = month_stat.get("keyword_synonym_groups", [])
    report["photo_library"] = [
        {
            "diary_id": r["diary_id"],
            "date": r["date"],
            "image_url": r["source_image_url"],
            "full_image_url": r["source_full_image_url"],
            "content": r["content"],
        }
        for r in month_stat["raw_scenes"]
    ]
    return report


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
    scenes = _get_scenes_for_month(diaries, target_month, scene_map)
    month_stat = _compute_monthly_stats(scenes)
    highlights = _select_highlights(month_stat, top_k=3)

    # 현재 서버에서는 GPT_REPORT는 옵션으로 남겨둔다.
    # notebook과 동일한 shape를 유지하되, 기본은 rule 기반.
    report = make_rule_based_month_report(target_month, month_stat, highlights)

    report["user_id"] = user_id
    report["generated_at"] = datetime.utcnow().isoformat()

    snapshot = {
        "source_diary_count": len(diaries),
        "last_source_created_at": diaries[-1].created_at if diaries else None,
        "source_hash": _compute_source_hash(diaries),
    }
    return report, snapshot


async def get_monthly_report_status(
    db: AsyncSession,
    user_id: int,
    target_month: str,
) -> dict:
    diaries = await _fetch_month_diaries(db, user_id, target_month)
    current_count = len(diaries)
    current_hash = _compute_source_hash(diaries) if diaries else ""

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
        stored.generation_version = "report_v4_notebook_like_server_v3"
    else:
        stored = MonthlyReport(
            user_id=user_id,
            target_month=target_month,
            report_json=payload,
            source_diary_count=snapshot["source_diary_count"],
            source_hash=snapshot["source_hash"],
            last_source_created_at=snapshot["last_source_created_at"],
            generation_version="report_v4_notebook_like_server_v3",
        )
        db.add(stored)

    await db.commit()
    await db.refresh(stored)
    return stored.report_json