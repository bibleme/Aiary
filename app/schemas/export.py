# app/schemas/export.py
from datetime import date, datetime
from typing import List, Optional

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
    content: str
    diary_date: date
    source_count: int
    created_at: datetime
    updated_at: datetime

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