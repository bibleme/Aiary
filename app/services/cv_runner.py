# app/services/cv_runner.py
from __future__ import annotations

import gc
import math
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from PIL import Image

from app.config import settings
from app.db.model import Diary
from app.services.cv_loader import load_cv_models
from app.services.image_resolver import (
    resolve_image_path_for_cv,
    cleanup_temp_image,
)


def classify_scene(models: dict[str, Any], image: Image.Image) -> tuple[str, list[float]]:
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


def bbox_center(box: list[float]) -> tuple[float, float]:
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def siglip_embedding(
    models: dict[str, Any],
    img_pil: Image.Image,
    box: list[float],
) -> list[float] | None:
    if not settings.CV_USE_SIGLIP_EMBEDDINGS:
        return None

    processor = models.get("siglip_processor")
    model = models.get("siglip_model")
    device = models["device"]

    if processor is None or model is None:
        return None

    w, h = img_pil.size
    x1, y1, x2, y2 = [int(v) for v in box]

    x1, x2 = max(0, min(x1, x2)), min(w, max(x1, x2))
    y1, y2 = max(0, min(y1, y2)), min(h, max(y1, y2))

    if x2 <= x1 or y2 <= y1:
        return None

    crop = img_pil.crop((x1, y1, x2, y2))

    inputs = processor(images=crop, return_tensors="pt").to(device)

    with torch.no_grad():
        feats = model.get_image_features(**inputs)
        feats = F.normalize(feats, dim=-1)

    return feats.squeeze(0).detach().cpu().tolist()


def detect_objects(
    models: dict[str, Any],
    image_path: Path,
    img_pil: Image.Image,
) -> list[dict]:
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

        if conf < 0.25:
            continue

        xyxy = b.xyxy[0].tolist()
        category = names.get(cls_idx, str(cls_idx))

        feature_vector = siglip_embedding(models, img_pil, xyxy)

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


def build_interactions(persons: list[dict], objects: list[dict]) -> list[dict]:
    interactions = []

    for p_idx, p in enumerate(persons):
        p_bbox = p.get("bbox")
        if not p_bbox:
            continue

        pc = bbox_center(p_bbox)

        best_obj_idx = None
        best_dist = None

        for o_idx, o in enumerate(objects):
            o_bbox = o.get("bbox")
            if not o_bbox:
                continue

            oc = bbox_center(o_bbox)
            dist = distance(pc, oc)

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
    if not settings.CV_ENABLED:
        raise RuntimeError("CV is disabled by settings.CV_ENABLED=False")

    models = load_cv_models()

    image_path, is_temp = resolve_image_path_for_cv(
        image_url=diary.image_url,
        image_storage=getattr(diary, "image_storage", "local"),
        image_key=getattr(diary, "image_key", None),
    )

    if not image_path.exists():
        raise FileNotFoundError(f"이미지 파일이 존재하지 않습니다: {image_path}")

    try:
        img_pil = Image.open(image_path).convert("RGB")

        predicted_tag, scene_vector = classify_scene(models, img_pil)
        objects = detect_objects(models, image_path, img_pil)

        # t3.small 안정판:
        # DeepFace / face CV는 여기서 돌리지 않는다.
        target_child_found = False
        target_child_confidence = None
        persons: list[dict] = []

        interactions = build_interactions(persons, objects)

        return {
            "predicted_tag": predicted_tag,
            "scene_vector": scene_vector,
            "target_child_found": target_child_found,
            "target_child_confidence": target_child_confidence,
            "persons": persons,
            "objects": objects,
            "interactions": interactions,
        }

    finally:
        cleanup_temp_image(image_path, is_temp)
        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()