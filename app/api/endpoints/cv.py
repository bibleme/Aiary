# app/api/endpoints/cv.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.api.endpoints.user import get_current_user
from app.db.model import User
from app.db import crud
from app.schemas.cv import (
    CVMonthlySummaryResponse,
    CVProcessResponse,
    CVStatusResponse,
)
from app.services.cv_runner import run_cv_for_diary
from app.services.cv_monthly_summary import generate_cv_monthly_summary

router = APIRouter(prefix="/cv", tags=["cv"])


@router.post("/process/{one_line_diary_id}", response_model=CVProcessResponse)
async def process_cv_for_one_diary(
    one_line_diary_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    diary = await crud.get_diary_by_id(db, one_line_diary_id)
    if diary is None:
        raise HTTPException(status_code=404, detail="한줄일기를 찾을 수 없습니다.")
    if diary.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    vision_image = await crud.get_or_create_vision_image(db, diary)

    try:
        result = await run_cv_for_diary(diary)
        vision_image = await crud.save_cv_result(
            db=db,
            vision_image=vision_image,
            predicted_tag=result.get("predicted_tag"),
            scene_vector=result.get("scene_vector"),
            target_child_found=result.get("target_child_found", False),
            target_child_confidence=result.get("target_child_confidence"),
            persons=result.get("persons", []),
            objects=result.get("objects", []),
            interactions=result.get("interactions", []),
        )
        return CVProcessResponse(
            one_line_diary_id=one_line_diary_id,
            vision_image_id=vision_image.id,
            cv_status=vision_image.cv_status,
            message="CV 분석이 완료되었습니다.",
        )
    except Exception as e:
        vision_image = await crud.mark_vision_failed(db, vision_image, str(e))
        raise HTTPException(status_code=500, detail=f"CV 분석 실패: {e}")


@router.get("/status/{one_line_diary_id}", response_model=CVStatusResponse)
async def get_cv_status(
    one_line_diary_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    diary = await crud.get_diary_by_id(db, one_line_diary_id)
    if diary is None:
        raise HTTPException(status_code=404, detail="한줄일기를 찾을 수 없습니다.")
    if diary.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    vision_image = await crud.get_vision_image_by_diary_id(db, one_line_diary_id)
    if vision_image is None:
        return CVStatusResponse(
            one_line_diary_id=one_line_diary_id,
            cv_status="pending",
            predicted_tag=None,
            target_child_found=False,
            processed_at=None,
            error_message=None,
        )

    return CVStatusResponse(
        one_line_diary_id=one_line_diary_id,
        cv_status=vision_image.cv_status,
        predicted_tag=vision_image.predicted_tag,
        target_child_found=vision_image.target_child_found,
        processed_at=vision_image.processed_at,
        error_message=vision_image.error_message,
    )


@router.get("/monthly", response_model=CVMonthlySummaryResponse)
async def get_cv_monthly_summary(
    target_month: str = Query(..., regex=r"^\d{4}-\d{2}$"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    result = await generate_cv_monthly_summary(
        db=db,
        user_id=current_user.id,
        target_month=target_month,
    )
    return CVMonthlySummaryResponse(**result)