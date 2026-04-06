from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.model import User
from app.schemas.monthly_report import MonthlyReportResponse
from app.services.monthly_report_loader import get_monthly_report_for_user
from app.services.security import get_current_user

router = APIRouter(prefix="/monthly-report", tags=["monthly-report"])


@router.get("", response_model=MonthlyReportResponse)
async def get_monthly_report(
    target_month: str = Query(..., description="조회할 연월 (예: 2026-03)"),
    current_user: User = Depends(get_current_user),
):
    try:
        report = get_monthly_report_for_user(current_user.id, target_month)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 유저/월의 리포트가 존재하지 않습니다.",
            )
        return report
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
