# app/api/endpoints/export.py
import calendar
from datetime import date
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.db.model import Diary, DailyDiary, User
from app.schemas.export import (
    DailyDiaryItem,
    MonthlyDiariesResponse,
    MonthlyDiaryDay,
    OneLineDiaryItem,
)
from app.services.security import get_current_user

router = APIRouter(prefix="/exports", tags=["exports"])

from typing import List
from pydantic import BaseModel
class UserDiariesResponse(BaseModel):
    user_id: int
    diaries: List[OneLineDiaryItem]


@router.get("/monthly-diaries", response_model=MonthlyDiariesResponse)
async def get_monthly_diaries(
    year: int = Query(..., ge=1900, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    로그인한 사용자의 특정 연/월(one-line + daily) 데이터를 날짜별로 묶어서 반환한다.
    데이터가 없는 날짜도 month 전체 일자에 대해 모두 포함한다.
    """
    try:
        start_date = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 year/month 값입니다.",
        )

    one_line_stmt = (
        select(Diary)
        .where(
            Diary.user_id == current_user.id,
            Diary.diary_date >= start_date,
            Diary.diary_date <= end_date,
        )
        .order_by(Diary.diary_date.asc(), Diary.created_at.asc(), Diary.id.asc())
    )
    one_line_result = await db.execute(one_line_stmt)
    one_line_diaries = one_line_result.scalars().all()

    daily_stmt = (
        select(DailyDiary)
        .where(
            DailyDiary.user_id == current_user.id,
            DailyDiary.diary_date >= start_date,
            DailyDiary.diary_date <= end_date,
        )
        .order_by(DailyDiary.diary_date.asc(), DailyDiary.id.asc())
    )
    daily_result = await db.execute(daily_stmt)
    daily_diaries = daily_result.scalars().all()

    days_map: dict[date, MonthlyDiaryDay] = {}
    for day_num in range(1, last_day + 1):
        current_date = date(year, month, day_num)
        days_map[current_date] = MonthlyDiaryDay(
            date=current_date,
            one_line_diaries=[],
            daily_diary=None,
        )

    for diary in one_line_diaries:
        days_map[diary.diary_date].one_line_diaries.append(
            OneLineDiaryItem.model_validate(diary)
        )

    for daily in daily_diaries:
        days_map[daily.diary_date].daily_diary = DailyDiaryItem.model_validate(daily)

    return MonthlyDiariesResponse(
        user_id=current_user.id,
        year=year,
        month=month,
        days=list(days_map.values()),
    )

@router.get("/admin/one-line-list", response_model=List[UserDiariesResponse])
async def get_all_users_diaries_for_admin(
    db: AsyncSession = Depends(get_db_session)
):
    """
    [개발자/관리자 전용] 모든 유저의 한 줄 일기를 가져와서,
    user_id가 명시된 리스트 형태로 반환합니다. (정렬 완벽 보장)
    """
    # 🌟 수정 포인트 1: 정렬 기준 마지막에 'Diary.id.desc()'를 추가!
    # (유저순 -> 날짜 최신순 -> 같은 날짜면 ID 최신순)
    stmt = (
        select(Diary)
        .order_by(Diary.user_id.asc(), Diary.diary_date.asc(), Diary.id.asc())
    )
    result = await db.execute(stmt)
    all_diaries = result.scalars().all()

    grouped_diaries = defaultdict(list)
    for diary in all_diaries:
        grouped_diaries[diary.user_id].append(OneLineDiaryItem.model_validate(diary))

    response_data = []
    # 🌟 수정 포인트 2: response_data에 담을 때 user_id를 '명시적으로 오름차순 정렬'해서 담기
    for uid in sorted(grouped_diaries.keys()):
        response_data.append(
            UserDiariesResponse(user_id=uid, diaries=grouped_diaries[uid])
        )

    return response_data