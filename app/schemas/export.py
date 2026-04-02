# app/schemas/export.py
from datetime import date, datetime
from typing import List, Optional, Any

from pydantic import BaseModel


class OneLineDiaryItem(BaseModel):
    id: int
    content: str
    image_url: str
    diary_date: date
    created_at: datetime

    class Config:
        from_attributes = True


class DailyDiaryItem(BaseModel):
    id: int
    diary_date: date

    content: str   # 하위호환용 = final_content
    generated_content: str
    edited_content: Optional[str] = None
    final_content: str

    model_version: Optional[str] = None
    generation_meta: Optional[Any] = None

    source_count: int
    created_at: datetime
    updated_at: datetime
    edited_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MonthlyDiaryDay(BaseModel):
    date: date
    one_line_diaries: List[OneLineDiaryItem]
    daily_diary: Optional[DailyDiaryItem] = None


class MonthlyDiariesResponse(BaseModel):
    user_id: int
    year: int
    month: int
    days: List[MonthlyDiaryDay]
    
    
class AdminOneLineDiaryItem(BaseModel):
    id: int
    content: str
    image_url: str
    diary_date: date
    created_at: datetime

    class Config:
        from_attributes = True


class UserDiariesResponse(BaseModel):
    user_id: int
    diaries: List[AdminOneLineDiaryItem]    