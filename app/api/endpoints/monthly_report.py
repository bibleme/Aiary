# app/api/endpoints/monthly_report.py

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db_session
from app.db.model import MonthlyReport, User
from app.schemas.monthly_report import (
    MonthlyReportResponse,
    MonthlyReportStatusResponse,
)
from app.services.monthly_report_generator import (
    generate_and_store_monthly_report,
    get_monthly_report_status,
    refresh_monthly_report_image_urls,
)
from app.services.monthly_report_loader import get_monthly_report_for_user
from app.services.security import get_current_user

router = APIRouter(prefix="/monthly-report", tags=["monthly-report"])


@router.get("", response_model=MonthlyReportResponse)
async def get_monthly_report(
    target_month: str = Query(..., description="조회할 연월 (예: 2026-03)"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MonthlyReport).where(
            MonthlyReport.user_id == current_user.id,
            MonthlyReport.target_month == target_month,
        )
    )
    stored = result.scalar_one_or_none()

    if stored:
        return await refresh_monthly_report_image_urls(
            db=db,
            user_id=current_user.id,
            report=stored.report_json,
        )

    if settings.MONTHLY_REPORT_USE_JSON_FALLBACK:
        fallback = get_monthly_report_for_user(current_user.id, target_month)
        if fallback:
            return fallback

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="해당 유저/월의 리포트가 존재하지 않습니다.",
    )


@router.get("/status", response_model=MonthlyReportStatusResponse)
async def get_monthly_report_status_api(
    target_month: str = Query(..., description="조회할 연월 (예: 2026-03)"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    try:
        return await get_monthly_report_status(
            db=db,
            user_id=current_user.id,
            target_month=target_month,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/generate", response_model=MonthlyReportResponse)
async def generate_monthly_report_api(
    target_month: str = Query(..., description="생성할 연월 (예: 2026-03)"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    try:
        report = await generate_and_store_monthly_report(
            db=db,
            user_id=current_user.id,
            target_month=target_month,
        )
        return await refresh_monthly_report_image_urls(
            db=db,
            user_id=current_user.id,
            report=report,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"월별 리포트 생성 중 서버 오류가 발생했습니다: {str(e)}",
        )


@router.post("/regenerate", response_model=MonthlyReportResponse)
async def regenerate_monthly_report_api(
    target_month: str = Query(..., description="재생성할 연월 (예: 2026-03)"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    try:
        report = await generate_and_store_monthly_report(
            db=db,
            user_id=current_user.id,
            target_month=target_month,
        )
        return await refresh_monthly_report_image_urls(
            db=db,
            user_id=current_user.id,
            report=report,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"월별 리포트 재생성 중 서버 오류가 발생했습니다: {str(e)}",
        )

