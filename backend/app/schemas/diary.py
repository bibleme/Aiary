# app/schemas/diary.py
import datetime
from datetime import date

from pydantic import BaseModel, Field


class OneLineDiaryResponse(BaseModel):
    id: int
    user_id: int
    content: str
    image_url: str
    diary_date: date
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class DailyDiaryCreateRequest(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")


class DailyDiaryResponse(BaseModel):
    id: int
    user_id: int
    diary_date: date
    content: str
    source_count: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True
