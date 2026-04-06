from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ReportPhotoRef(BaseModel):
    diary_id: Optional[int] = None
    date: Optional[str] = None
    image_url: Optional[str] = None
    full_image_url: Optional[str] = None
    content: Optional[str] = None


class ReportHighlightItem(BaseModel):
    date: Optional[str] = None
    text: Optional[str] = None
    raw_text: Optional[str] = None
    source_diary_id: Optional[int] = None
    source_image_url: Optional[str] = None
    source_full_image_url: Optional[str] = None
    keywords: List[str] = []
    annotations: Dict[str, Any] = {}
    fallback_photos: List[Dict[str, Any]] = []


class MonthlyReportResponse(BaseModel):
    user_id: int
    month: str
    mode: Optional[str] = None

    month_overview: Optional[str] = None
    pattern_summary: Optional[str] = None
    change_summary: Optional[str] = None
    parent_note: Optional[str] = None
    one_line_summary: Optional[str] = None

    highlights: List[ReportHighlightItem] = []
    keyword_annotations: Dict[str, Any] = {}
    keyword_photo_index: Dict[str, Any] = {}
    photo_library: List[ReportPhotoRef] = []
