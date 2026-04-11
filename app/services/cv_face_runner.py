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

    persons = []
    for idx, item in enumerate(results):
        region = item.get("region") or {}
        bbox = [
            float(region.get("x", 0)),
            float(region.get("y", 0)),
            float(region.get("x", 0) + region.get("w", 0)),
            float(region.get("y", 0) + region.get("h", 0)),
        ]
        emotion = item.get("dominant_emotion")
        emotions = item.get("emotion") or {}
        emotion_score = float(emotions.get(emotion, 0.0)) if emotion else None

        role = "other"
        if idx == 0 and target_child_found:
            role = "target_child"
        elif idx == 0 and not target_child_found:
            role = "assumed_child"
        elif idx > 0 and target_child_found:
            role = "adult_helper"

        persons.append(
            {
                "role": role,
                "emotion": emotion,
                "emotion_score": emotion_score,
                "bbox": bbox,
                "face_confidence": emotion_score,
            }
        )

    return persons