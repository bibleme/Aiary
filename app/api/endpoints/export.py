# app/api/endpoints/export.py

import calendar
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.db.model import Diary, DailyDiary, User
from app.schemas.export import (
    AdminOneLineDiaryItem,
    DailyDiaryItem,
    MonthlyDiariesResponse,
    MonthlyDiaryDay,
    OneLineDiaryItem,
    UserDiariesResponse,
)
from app.services.security import get_current_user
from app.services.storage import generate_presigned_image_url

router = APIRouter(prefix="/exports", tags=["exports"])


def _resolve_diary_image_url(diary: Diary) -> str:
    return generate_presigned_image_url(
        image_storage=getattr(diary, "image_storage", None),
        image_key=getattr(diary, "image_key", None),
        image_url=diary.image_url,
    )


@router.get("/monthly-diaries", response_model=MonthlyDiariesResponse)
async def get_monthly_diaries(
    year: int = Query(..., ge=1900, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
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
            OneLineDiaryItem(
                id=diary.id,
                content=diary.content,
                image_url=_resolve_diary_image_url(diary),
                diary_date=diary.diary_date,
                created_at=diary.created_at,
            )
        )

    for daily in daily_diaries:
        generated_content = daily.generated_content or daily.content or ""
        final_content = daily.edited_content or daily.generated_content or daily.content or ""

        days_map[daily.diary_date].daily_diary = DailyDiaryItem(
            id=daily.id,
            diary_date=daily.diary_date,
            content=final_content,
            generated_content=generated_content,
            edited_content=daily.edited_content,
            final_content=final_content,
            model_version=daily.model_version,
            generation_meta=daily.generation_meta,
            source_count=daily.source_count,
            created_at=daily.created_at,
            updated_at=daily.updated_at,
            edited_at=daily.edited_at,
        )

    return MonthlyDiariesResponse(
        user_id=current_user.id,
        year=year,
        month=month,
        days=list(days_map.values()),
    )


@router.get("/admin/one-line-list", response_model=list[UserDiariesResponse])
async def get_all_users_diaries_for_admin(
    user_id: int | None = Query(
        None,
        description="특정 유저의 한줄일기만 조회하고 싶을 때 사용",
    ),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Diary)

    if user_id is not None:
        stmt = stmt.where(Diary.user_id == user_id)

    stmt = stmt.order_by(Diary.user_id.asc(), Diary.diary_date.asc(), Diary.id.asc())

    result = await db.execute(stmt)
    all_diaries = result.scalars().all()

    grouped_diaries = defaultdict(list)

    for diary in all_diaries:
        grouped_diaries[diary.user_id].append(
            AdminOneLineDiaryItem(
                id=diary.id,
                content=diary.content,
                image_url=_resolve_diary_image_url(diary),
                diary_date=diary.diary_date,
                created_at=diary.created_at,
            )
        )

    response_data = []
    for uid in sorted(grouped_diaries.keys()):
        response_data.append(
            UserDiariesResponse(
                user_id=uid,
                diaries=grouped_diaries[uid],
            )
        )

    return response_data