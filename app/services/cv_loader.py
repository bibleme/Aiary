# app/services/cv_loader.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import torch

from app.config import settings

_MODELS: dict[str, Any] | None = None


def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _load_yolo_trusted(weights_path: str):
    from ultralytics import YOLO

    original_torch_load = torch.load

    def patched_torch_load(*args, **kwargs):
        kwargs["weights_only"] = False
        return original_torch_load(*args, **kwargs)

    torch.load = patched_torch_load
    try:
        model = YOLO(weights_path)
    finally:
        torch.load = original_torch_load

    return model


def load_cv_models() -> dict[str, Any]:
    global _MODELS

    if _MODELS is not None:
        return _MODELS

    os.environ.setdefault("HF_HOME", str(Path(settings.CV_CACHE_ROOT) / "huggingface"))
    os.environ.setdefault("TORCH_HOME", str(Path(settings.CV_CACHE_ROOT) / "torch"))
    os.environ.setdefault("DEEPFACE_HOME", str(Path(settings.CV_CACHE_ROOT) / "deepface"))

    import clip

    device = get_device()

    print("[CV] loading models...", flush=True)
    print(f"[CV] device={device}", flush=True)
    print(f"[CV] load_pose={settings.CV_LOAD_POSE_MODEL}", flush=True)
    print(f"[CV] use_siglip={settings.CV_USE_SIGLIP_EMBEDDINGS}", flush=True)

    yolo_obj = _load_yolo_trusted(settings.CV_YOLO_OBJECT_MODEL)

    yolo_pose = None
    if settings.CV_LOAD_POSE_MODEL:
        yolo_pose = _load_yolo_trusted(settings.CV_YOLO_POSE_MODEL)

    clip_model, clip_preprocess = clip.load(settings.CV_CLIP_MODEL_NAME, device=device)

    siglip_processor = None
    siglip_model = None
    if settings.CV_USE_SIGLIP_EMBEDDINGS:
        from transformers import AutoProcessor, AutoModel

        siglip_processor = AutoProcessor.from_pretrained(settings.CV_SIGLIP_MODEL_NAME)
        siglip_model = AutoModel.from_pretrained(settings.CV_SIGLIP_MODEL_NAME).to(device)
        siglip_model.eval()

    prompts = [
        "a photo of a residential home interior or living room",
        "a photo of a house with play mats and toys",
        "a photo of a daycare center or kindergarten classroom",
        "a photo of a kids cafe or indoor children's playground",
        "a photo of an aquarium or museum interior",
        "a photo of an exhibition or art gallery",
        "a photo of an indoor amusement park or large shopping mall",
        "a photo of a fancy restaurant, cafe, or hotel interior",
        "a photo of a nature park, forest, or outdoor playground",
        "a photo of the beach or sea",
        "a photo of a zoo or botanical garden",
        "a photo of a city street or outdoor building exterior",
        "an extreme close-up photo of an object, food, or toy",
        "a blurry photo or texture without a visible background",
        "a photo of a plain floor, wall, or ceiling",
    ]

    prompt_to_tag = {
        prompts[0]: "Routine_Indoor",
        prompts[1]: "Routine_Indoor",
        prompts[2]: "Routine_Indoor",
        prompts[3]: "Routine_Indoor",
        prompts[4]: "Special_Outing",
        prompts[5]: "Special_Outing",
        prompts[6]: "Special_Outing",
        prompts[7]: "Special_Outing",
        prompts[8]: "Outdoor_Outing",
        prompts[9]: "Outdoor_Outing",
        prompts[10]: "Outdoor_Outing",
        prompts[11]: "Outdoor_Outing",
        prompts[12]: "No_Scene",
        prompts[13]: "No_Scene",
        prompts[14]: "No_Scene",
    }

    tokens = clip.tokenize(prompts).to(device)

    with torch.no_grad():
        text_features = clip_model.encode_text(tokens)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)

    _MODELS = {
        "device": device,
        "yolo_obj": yolo_obj,
        "yolo_pose": yolo_pose,
        "clip_model": clip_model,
        "clip_preprocess": clip_preprocess,
        "siglip_model": siglip_model,
        "siglip_processor": siglip_processor,
        "prompts": prompts,
        "prompt_to_tag": prompt_to_tag,
        "text_features": text_features,
    }

    print("[CV] models loaded", flush=True)
    return _MODELS