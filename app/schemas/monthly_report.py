from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ReportPhotoRef(BaseModel):
    diary_id: Optional[int] = None
    date: Optional[str] = None
    image_url: Optional[str] = None
    full_image_url: Optional[str] = None
    content: Optional[str] = None


class ReportKeywordItem(BaseModel):
    keyword: Optional[str] = None
    keyword_type: Optional[str] = None
    dates: List[str] = []
    photo_count: Optional[int] = None
    photos: List[ReportPhotoRef] = []


class ReportAnnotationItem(BaseModel):
    start: Optional[int] = None
    end: Optional[int] = None
    keyword: Optional[str] = None
    keyword_type: Optional[str] = None
    dates: List[str] = []
    photo_count: Optional[int] = None
    photos: List[ReportPhotoRef] = []


class ReportHighlightItem(BaseModel):
    date: Optional[str] = None
    text: Optional[str] = None
    raw_text: Optional[str] = None
    source_diary_id: Optional[int] = None
    source_image_url: Optional[str] = None
    source_full_image_url: Optional[str] = None

    # 실제 JSON은 문자열 배열이 아니라 객체 배열
    keywords: List[ReportKeywordItem] = []

    # 실제 JSON은 dict가 아니라 list
    annotations: List[ReportAnnotationItem] = []

    fallback_photos: List[ReportPhotoRef] = []


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

    generated_at: Optional[datetime] = None
    
class MonthlyReportStatusResponse(BaseModel):
    user_id: int
    month: str
    exists: bool
    is_up_to_date: bool
    source_diary_count: int
    stored_source_diary_count: Optional[int] = None
    generated_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    reason: Optional[str] = None