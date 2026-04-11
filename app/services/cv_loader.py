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


def _register_ultralytics_safe_globals() -> None:
    """
    PyTorch 2.6+에서 torch.load 기본값이 weights_only=True로 바뀌면서
    Ultralytics YOLO 체크포인트 로딩 시 safe globals 등록이 필요할 수 있음.
    """
    try:
        from ultralytics.nn.tasks import DetectionModel, PoseModel
        torch.serialization.add_safe_globals([DetectionModel, PoseModel])
    except Exception:
        # 환경에 따라 내부 클래스 import가 달라질 수 있으므로,
        # 여기서 실패해도 아래 YOLO 로드 시도는 계속 진행한다.
        pass


def load_cv_models() -> dict[str, Any]:
    global _MODELS
    if _MODELS is not None:
        return _MODELS

    os.environ.setdefault("HF_HOME", str(Path(settings.CV_CACHE_ROOT) / "huggingface"))
    os.environ.setdefault("TORCH_HOME", str(Path(settings.CV_CACHE_ROOT) / "torch"))
    os.environ.setdefault("DEEPFACE_HOME", str(Path(settings.CV_CACHE_ROOT) / "deepface"))

    _register_ultralytics_safe_globals()

    from ultralytics import YOLO
    import clip
    from transformers import AutoProcessor, AutoModel

    device = get_device()

    # YOLO weights 로드
    yolo_obj = YOLO(settings.CV_YOLO_OBJECT_MODEL)
    yolo_pose = YOLO(settings.CV_YOLO_POSE_MODEL)

    # CLIP 로드
    clip_model, clip_preprocess = clip.load(settings.CV_CLIP_MODEL_NAME, device=device)

    # SigLIP 로드
    siglip_processor = AutoProcessor.from_pretrained(settings.CV_SIGLIP_MODEL_NAME)
    siglip_model = AutoModel.from_pretrained(settings.CV_SIGLIP_MODEL_NAME).to(device)

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
    return _MODELS