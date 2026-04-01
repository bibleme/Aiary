# app/api/endpoints/report.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

# 사용자님의 DB 세션 주입 함수 경로 (실제 파일 위치에 맞게 수정해주세요)
from app.db.database import get_db_session

# 방금 만든 비즈니스 로직 함수 불러오기
from app.services.report_generator import generate_monthly_report

router = APIRouter()

@router.get("/monthly", summary="CV 아웃풋 조회")
async def get_monthly_report(
    user_id: int = Query(..., description="조회할 유저의 ID"),
    target_month: str = Query(..., description="조회할 연월 (예: '2026-03')"),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    특정 유저의 월간 육아 비전 분석 리포트를 조회하여 프론트엔드용 JSON으로 반환합니다.
    """
    try:
        # 1. 아까 만든 함수에 DB 세션(db)과 파라미터들을 그대로 토스합니다!
        report_data = await generate_monthly_report(db, user_id=user_id, target_month=target_month)
        
        # 2. 성공적으로 데이터를 가져왔다면 프론트엔드로 응답을 보냅니다.
        return {
            "status": "success",
            "message": f"{target_month} 월간 리포트 조회가 완료되었습니다.",
            "data": report_data
        }
        
    except Exception as e:
        # 에러가 발생하면 500 에러를 던져 프론트엔드가 알 수 있게 합니다.
        raise HTTPException(status_code=500, detail=f"리포트 생성 중 서버 오류가 발생했습니다: {str(e)}")