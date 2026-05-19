# app/services/cv_face_runner.py
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import settings


def get_user_child_refs(user_id: int) -> list[Path]:
    user_dir = Path(settings.CV_CHILD_REFS_ROOT) / str(user_id)
    if user_dir.exists():
        refs = sorted(
            list(user_dir.glob("*.jpg"))
            + list(user_dir.glob("*.jpeg"))
            + list(user_dir.glob("*.png"))
        )
        if refs:
            return refs

    root_dir = Path(settings.CV_CHILD_REFS_ROOT)
    refs = sorted(
        list(root_dir.glob("*.jpg"))
        + list(root_dir.glob("*.jpeg"))
        + list(root_dir.glob("*.png"))
    )
    return refs


def verify_target_child(image_path: Path, ref_paths: list[Path]) -> tuple[bool, float | None]:
    if not ref_paths:
        return False, None

    from deepface import DeepFace

    best_distance = None
    for ref in ref_paths:
        try:
            result = DeepFace.verify(
                img1_path=str(image_path),
                img2_path=str(ref),
                enforce_detection=False,
                detector_backend="opencv",
                model_name="VGG-Face",
            )
            distance = float(result.get("distance", 999.0))
            if best_distance is None or distance < best_distance:
                best_distance = distance
        except Exception:
            continue

    if best_distance is None:
        return False, None

    return best_distance <= settings.CV_TARGET_CHILD_VERIFY_THRESHOLD, best_distance


def analyze_faces(image_path: Path, target_child_found: bool) -> list[dict[str, Any]]:
    from deepface import DeepFace
    from PIL import Image
    
    #너무 작은 얼굴 제외
    MIN_FACE_WIDTH = 90
    MIN_FACE_HEIGHT = 90
    MIN_FACE_AREA_RATIO = 0.006

    try:
        img = Image.open(image_path)
        image_w, image_h = img.size
        image_area = max(image_w * image_h, 1)
    except Exception:
        image_w, image_h, image_area = 0, 0, 1

    try:
        results = DeepFace.analyze(
            img_path=str(image_path),
            actions=["emotion"],
            enforce_detection=False,
            detector_backend="opencv",
        )
    except Exception:
        return []

    if isinstance(results, dict):
        results = [results]

    candidates = []

    for item in results:
        region = item.get("region") or {}

        x = float(region.get("x", 0))
        y = float(region.get("y", 0))
        w = float(region.get("w", 0))
        h = float(region.get("h", 0))

        if w <= 0 or h <= 0:
            continue

        area = w * h
        area_ratio = area / image_area

        if w < MIN_FACE_WIDTH or h < MIN_FACE_HEIGHT:
            continue

        if area_ratio < MIN_FACE_AREA_RATIO:
            continue

        emotion = item.get("dominant_emotion")
        emotions = item.get("emotion") or {}
        emotion_score = float(emotions.get(emotion, 0.0)) if emotion else None

        candidates.append(
            {
                "emotion": emotion,
                "emotion_score": emotion_score,
                "bbox": [x, y, x + w, y + h],
                "face_confidence": emotion_score,
                "_area": area,
            }
        )

    if not candidates:
        return []

    candidates.sort(key=lambda x: x["_area"], reverse=True)

    persons = []
    for idx, item in enumerate(candidates):
        role = "other"

        if idx == 0 and target_child_found:
            role = "target_child"
        elif idx == 0:
            role = "assumed_child"
        elif target_child_found:
            role = "adult_helper"

        persons.append(
            {
                "role": role,
                "emotion": item["emotion"],
                "emotion_score": item["emotion_score"],
                "bbox": item["bbox"],
                "face_confidence": item["face_confidence"],
            }
        )

    return persons