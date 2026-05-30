# app/schemas/cv.py

from datetime import datetime
from typing import List, Optional, Literal, Any
from pydantic import BaseModel, Field


class AppearanceBBox(BaseModel):
    file_name: str
    bbox: list[float]


class FavoriteObjectItem(BaseModel):
    rank: int
    category: str
    category_kr: Optional[str] = None
    is_new: bool
    photo_count: int
    photos: List[str] = Field(default_factory=list)
    appearances: List[AppearanceBBox] = Field(default_factory=list)


class BestCut(BaseModel):
    file_name: str
    confidence: float
    bbox: list[float]


class EmotionSummaryItem(BaseModel):
    emotion_en: str
    emotion_kr: str
    ratio: float
    best_cut: BestCut


class HighlightPlaceItem(BaseModel):
    rank: int
    place_key: str
    place_label: str
    is_new: bool
    photo_count: int
    photos: List[str]


class CVMonthlySummaryResponse(BaseModel):
    report_month: str
    favorite_objects: List[FavoriteObjectItem] = Field(default_factory=list)
    emotions_summary: List[EmotionSummaryItem] = Field(default_factory=list)
    highlight_places: List[HighlightPlaceItem] = Field(default_factory=list)


class CVStatusResponse(BaseModel):
    one_line_diary_id: int
    cv_status: Literal["pending", "done", "failed"]
    predicted_tag: Optional[str] = None
    target_child_found: bool = False
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class CVProcessResponse(BaseModel):
    one_line_diary_id: int
    vision_image_id: int
    cv_status: Literal["pending", "done", "failed"]
    message: str

class CVPhotoItem(BaseModel):
    diary_id: Optional[int] = None
    vision_image_id: Optional[int] = None
    date: Optional[str] = None
    file_name: Optional[str] = None
    image_url: Optional[str] = None
    bbox: Optional[list[float]] = None
    confidence: Optional[float] = None


class CVFavoriteObject(BaseModel):
    rank: int
    category: str
    category_kr: str
    is_new: bool
    photo_count: int
    photos: list[str] = []
    photo_items: list[CVPhotoItem] = []
    appearances: list[CVPhotoItem] = []


class CVEmotionSummary(BaseModel):
    emotion_en: str
    emotion_kr: str
    ratio: float
    best_cut: CVPhotoItem


class CVHighlightPlace(BaseModel):
    rank: int
    place_key: str
    place_label: str
    is_new: bool
    photo_count: int
    photos: list[str] = []
    photo_items: list[CVPhotoItem] = []


class CVEmotionBasis(BaseModel):
    description: str
    analyzed_face_count: int
    is_reference_only: bool


class CVMonthlySummaryResponse(BaseModel):
    report_month: str
    favorite_objects: list[CVFavoriteObject] = []
    emotions_summary: list[CVEmotionSummary] = []
    highlight_places: list[CVHighlightPlace] = []
    emotion_basis: Optional[CVEmotionBasis] = None

class AppearanceIn(BaseModel):
    entity_type: Literal["person", "object"]
    entity_index: int
    bbox: list[float]
    confidence: Optional[float] = None


class PersonIn(BaseModel):
    role: str
    emotion: Optional[str] = None
    emotion_score: Optional[float] = None
    bbox: Optional[list[float]] = None
    face_confidence: Optional[float] = None


class ObjectIn(BaseModel):
    base_category: str
    feature_vector: Optional[list[float]] = None
    parent_assigned_name: Optional[str] = None
    first_seen_vision_image_id: Optional[int] = None
    bbox: Optional[list[float]] = None
    confidence: Optional[float] = None


class InteractionIn(BaseModel):
    person_index: int
    object_index: int
    interaction_type: Optional[str] = None
    proximity_score: Optional[float] = None


class CVIngestRequest(BaseModel):
    predicted_tag: Optional[str] = None
    scene_vector: Optional[list[float]] = None
    target_child_found: bool = False
    target_child_confidence: Optional[float] = None
    persons: List[PersonIn] = Field(default_factory=list)
    objects: List[ObjectIn] = Field(default_factory=list)
    interactions: List[InteractionIn] = Field(default_factory=list)
    
