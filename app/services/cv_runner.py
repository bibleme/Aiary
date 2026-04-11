# app/services/cv_runner.py
# app/services/cv_runner.py
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from PIL import Image

from app.config import settings
from app.db.model import Diary
from app.services.cv_loader import load_cv_models

USE_DEEPFACE = False


def _resolve_local_image_path(image_url: str) -> Path:
    if image_url.startswith("/media/images/"):
        filename = image_url.split("/")[-1]
        return Path(settings.IMAGE_UPLOAD_DIR) / filename
    raise FileNotFoundError(f"지원하지 않는 image_url 형식입니다: {image_url}")


def _get_user_child_refs(user_id: int) -> list[Path]:
    user_dir = Path(settings.CV_CHILD_REFS_ROOT) / str(user_id)
    if user_dir.exists():
        refs = sorted(list(user_dir.glob("*.jpg")) + list(user_dir.glob("*.jpeg")) + list(user_dir.glob("*.png")))
        if refs:
            return refs

    root_dir = Path(settings.CV_CHILD_REFS_ROOT)
    refs = sorted(list(root_dir.glob("*.jpg")) + list(root_dir.glob("*.jpeg")) + list(root_dir.glob("*.png")))
    return refs


def _classify_scene(models: dict[str, Any], image: Image.Image) -> tuple[str, list[float]]:
    import clip

    device = models["device"]
    clip_model = models["clip_model"]
    preprocess = models["clip_preprocess"]
    prompts = models["prompts"]
    prompt_to_tag = models["prompt_to_tag"]
    text_features = models["text_features"]

    image_input = preprocess(image).unsqueeze(0).to(device)
    with torch.no_grad():
        image_features = clip_model.encode_image(image_input)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        logits = 100.0 * image_features @ text_features.T
        probs = logits.softmax(dim=-1)
        best_idx = int(probs.argmax(dim=-1).item())

    best_prompt = prompts[best_idx]
    predicted_tag = prompt_to_tag[best_prompt]
    scene_vector = image_features.squeeze(0).detach().cpu().tolist()
    return predicted_tag, scene_vector


def _bbox_center(box: list[float]) -> tuple[float, float]:
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _siglip_embedding(models: dict[str, Any], img_pil: Image.Image, box: list[float]) -> list[float]:
    processor = models["siglip_processor"]
    model = models["siglip_model"]
    device = models["device"]

    w, h = img_pil.size
    x1, y1, x2, y2 = [int(v) for v in box]
    x1, x2 = max(0, min(x1, x2)), min(w, max(x1, x2))
    y1, y2 = max(0, min(y1, y2)), min(h, max(y1, y2))
    crop = img_pil.crop((x1, y1, x2, y2))

    inputs = processor(images=crop, return_tensors="pt").to(device)
    with torch.no_grad():
        feats = model.get_image_features(**inputs)
        feats = F.normalize(feats, dim=-1)
    return feats.squeeze(0).detach().cpu().tolist()


def _verify_target_child(image_path: Path, ref_paths: list[Path]) -> tuple[bool, float | None]:
    if not ref_paths:
        return False, None

    try:
        from deepface import DeepFace
    except Exception:
        return False, None

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


def _analyze_faces(image_path: Path, target_child_found: bool) -> list[dict]:
    try:
        from deepface import DeepFace
    except Exception:
        return []

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


def _detect_objects(models: dict[str, Any], image_path: Path, img_pil: Image.Image) -> list[dict]:
    yolo_obj = models["yolo_obj"]
    result = yolo_obj(str(image_path), verbose=False)[0]

    objects = []
    names = result.names
    boxes = result.boxes

    if boxes is None:
        return objects

    for b in boxes:
        cls_idx = int(b.cls.item())
        conf = float(b.conf.item())
        xyxy = b.xyxy[0].tolist()
        category = names.get(cls_idx, str(cls_idx))
        feature_vector = _siglip_embedding(models, img_pil, xyxy)

        objects.append(
            {
                "base_category": category,
                "feature_vector": feature_vector,
                "parent_assigned_name": None,
                "first_seen_vision_image_id": None,
                "bbox": [float(v) for v in xyxy],
                "confidence": conf,
            }
        )
    return objects


def _build_interactions(persons: list[dict], objects: list[dict]) -> list[dict]:
    interactions = []
    for p_idx, p in enumerate(persons):
        p_bbox = p.get("bbox")
        if not p_bbox:
            continue
        pc = _bbox_center(p_bbox)

        best_obj_idx = None
        best_dist = None
        for o_idx, o in enumerate(objects):
            o_bbox = o.get("bbox")
            if not o_bbox:
                continue
            oc = _bbox_center(o_bbox)
            dist = _distance(pc, oc)
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_obj_idx = o_idx

        if best_obj_idx is not None:
            interactions.append(
                {
                    "person_index": p_idx,
                    "object_index": best_obj_idx,
                    "interaction_type": "near_hand",
                    "proximity_score": float(best_dist or 0.0),
                }
            )
    return interactions


async def run_cv_for_diary(diary: Diary) -> dict:
    models = load_cv_models()
    image_path = _resolve_local_image_path(diary.image_url)
    if not image_path.exists():
        raise FileNotFoundError(f"이미지 파일이 존재하지 않습니다: {image_path}")

    img_pil = Image.open(image_path).convert("RGB")

    predicted_tag, scene_vector = _classify_scene(models, img_pil)

    ref_paths = _get_user_child_refs(diary.user_id)

    if USE_DEEPFACE:
        target_child_found, target_child_confidence = _verify_target_child(image_path, ref_paths)
        persons = _analyze_faces(image_path, target_child_found)
    else:
        target_child_found, target_child_confidence = False, None
        persons = []

    objects = _detect_objects(models, image_path, img_pil)
    interactions = _build_interactions(persons, objects)

    return {
        "predicted_tag": predicted_tag,
        "scene_vector": scene_vector,
        "target_child_found": target_child_found,
        "target_child_confidence": target_child_confidence,
        "persons": persons,
        "objects": objects,
        "interactions": interactions,
    }