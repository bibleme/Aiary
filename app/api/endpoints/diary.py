# app/api/endpoints/diary.py
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud import get_or_create_vision_image
from app.db.database import get_db_session
from app.db.model import Diary, DailyDiary, User
from app.schemas.diary import (
    OneLineDiaryResponse,
    DailyDiaryResponse,
    DailyDiaryUpdateRequest,
)
from app.services.ai_generator import generate_one_line_diary
from app.services.daily_diary_generator import generate_daily_diary
from app.services.security import get_current_user
from app.config import settings
from app.services.storage import save_uploaded_image

router = APIRouter(tags=["diaries"])

GPT_USER_PROMPT = (
    "위 이미지를 보고 오늘 있었던 순간을 떠올리듯이 "
    "아이의 감정, 행동을 파악하고, 주변 사물로 상황을 파악하여 "
    "한국어로 25자 이내의 감성적인 한 줄 일기를 한 문장만 써줘. "
    "문장에 이모지를 적극적으로 활용하세요."
)

IMAGES_DIR = Path(settings.IMAGE_UPLOAD_DIR)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


class DaySummaryRequest(BaseModel):
    date: str  # YYYY-MM-DD


def _parse_date(date_str: str) -> date:
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date는 YYYY-MM-DD 형식이어야 합니다.",
        )


def _generate_filename(original_name: str) -> str:
    ext = Path(original_name).suffix or ".jpg"
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    uid = uuid4().hex[:8]
    return f"{ts}_{uid}{ext}"


def _serialize_diary(diary: Diary) -> dict:
    return {
        "id": diary.id,
        "user_id": diary.user_id,
        "content": diary.content,
        "image_url": diary.image_url,
        "diary_date": diary.diary_date,
        "created_at": diary.created_at,
    }

def _resolve_generated_content(daily_diary: DailyDiary) -> str:
    return daily_diary.generated_content or daily_diary.content or ""


def _resolve_final_content(daily_diary: DailyDiary) -> str:
    return daily_diary.edited_content or daily_diary.generated_content or daily_diary.content or ""


def _serialize_daily_diary(daily_diary: DailyDiary) -> dict:
    generated_content = _resolve_generated_content(daily_diary)
    final_content = _resolve_final_content(daily_diary)

    return {
        "id": daily_diary.id,
        "user_id": daily_diary.user_id,
        "diary_date": daily_diary.diary_date,
        "content": final_content,  # 하위호환용
        "generated_content": generated_content,
        "edited_content": daily_diary.edited_content,
        "final_content": final_content,
        "model_version": daily_diary.model_version,
        "generation_meta": daily_diary.generation_meta,
        "source_count": daily_diary.source_count,
        "created_at": daily_diary.created_at,
        "updated_at": daily_diary.updated_at,
        "edited_at": daily_diary.edited_at,
    }


async def _get_one_line_diaries_for_date(
    db: AsyncSession,
    user_id: int,
    target_date: date,
) -> list[Diary]:
    result = await db.execute(
        select(Diary)
        .where(
            Diary.user_id == user_id,
            Diary.diary_date == target_date,
        )
        .order_by(Diary.created_at.asc(), Diary.id.asc())
    )
    return list(result.scalars().all())


async def _get_daily_diary(
    db: AsyncSession,
    user_id: int,
    target_date: date,
) -> Optional[DailyDiary]:
    result = await db.execute(
        select(DailyDiary).where(
            DailyDiary.user_id == user_id,
            DailyDiary.diary_date == target_date,
        )
    )
    return result.scalar_one_or_none()


@router.post("/diaries/", response_model=OneLineDiaryResponse)
async def create_diary(
    photo: UploadFile = File(...),
    date_str: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    try:
        diary_date = _parse_date(date_str) if date_str else date.today()

        image_bytes = await photo.read()
        if not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="빈 이미지 파일입니다.",
            )

        one_line = await generate_one_line_diary(image_bytes, GPT_USER_PROMPT)

        storage_result = save_uploaded_image(
            image_bytes=image_bytes,
            user_id=current_user.id,
            original_filename=photo.filename or "image.jpg",
            content_type=photo.content_type,
            diary_date=diary_date,
        )

        new_diary = Diary(
            user_id=current_user.id,
            content=one_line,
            image_url=storage_result["image_url"],
            image_storage=storage_result["image_storage"],
            image_key=storage_result["image_key"],
            image_filename=storage_result["image_filename"],
            diary_date=diary_date,
        )

        db.add(new_diary)
        await db.commit()
        await db.refresh(new_diary)
        
        await get_or_create_vision_image(db, new_diary)

        return _serialize_diary(new_diary)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diary creation failed: {e}",
        )


@router.get("/diaries/", response_model=list[OneLineDiaryResponse])
async def list_diaries(
    date_str: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    try:
        stmt = select(Diary).where(Diary.user_id == current_user.id)

        if date_str:
            target_date = _parse_date(date_str)
            stmt = stmt.where(Diary.diary_date == target_date)

        stmt = stmt.order_by(desc(Diary.created_at), desc(Diary.id))

        result = await db.execute(stmt)
        diaries = result.scalars().all()

        return [_serialize_diary(diary) for diary in diaries]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diary list failed: {e}",
        )


@router.get("/diaries/{diary_id}", response_model=OneLineDiaryResponse)
async def get_one_line_diary(
    diary_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Diary).where(
            Diary.id == diary_id,
            Diary.user_id == current_user.id,
        )
    )
    diary = result.scalar_one_or_none()

    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 한줄일기가 존재하지 않습니다.",
        )

    return _serialize_diary(diary)


@router.delete("/diaries/{diary_id}")
async def delete_diary(
    diary_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            select(Diary).where(
                Diary.id == diary_id,
                Diary.user_id == current_user.id,
            )
        )
        diary = result.scalar_one_or_none()

        if diary is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 일기가 존재하지 않습니다.",
            )

        await db.delete(diary)
        await db.commit()

        return {
            "status": "success",
            "deleted_diary_id": diary_id,
            "message": "한줄일기가 삭제되었습니다.",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diary delete failed: {e}",
        )


@router.post("/daily-diaries/", response_model=DailyDiaryResponse)
async def create_daily_diary(
    payload: DaySummaryRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    try:
        target_date = _parse_date(payload.date)

        existing = await _get_daily_diary(db, current_user.id, target_date)
        if existing:
            return _serialize_daily_diary(existing)

        diaries = await _get_one_line_diaries_for_date(db, current_user.id, target_date)
        if not diaries:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 날짜에 한줄일기가 없습니다.",
            )

        one_lines = [diary.content for diary in diaries]

        gen_result = await generate_daily_diary(one_lines)
        full_diary = gen_result["generated_diary"]

        print(
            f"[daily-diary] user_id={current_user.id} "
            f"date={target_date} "
            f"model_version={gen_result.get('model_version', 'unknown')} "
            f"one_lines_count={len(one_lines)}",
            flush=True,
        )
        
        
        new_daily_diary = DailyDiary(
            user_id=current_user.id,
            diary_date=target_date,
            content=full_diary,  # 임시 호환용
            generated_content=full_diary,
            edited_content=None,
            model_version=gen_result.get("model_version"),
            generation_meta={
                "one_lines_count": gen_result.get("one_lines_count"),
                "bullet_lines": gen_result.get("bullet_lines"),
                "combined_summary": gen_result.get("combined_summary"),
            },
            source_count=len(one_lines),
        )

        db.add(new_daily_diary)
        await db.commit()
        await db.refresh(new_daily_diary)

        return _serialize_daily_diary(new_daily_diary)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Daily diary create failed: {e}",
        )


@router.get("/daily-diaries/{date_str}", response_model=DailyDiaryResponse)
async def get_daily_diary(
    date_str: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    try:
        target_date = _parse_date(date_str)

        existing = await _get_daily_diary(db, current_user.id, target_date)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 날짜의 하루일기가 아직 생성되지 않았습니다.",
            )

        return _serialize_daily_diary(existing)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Daily diary get failed: {e}",
        )


@router.patch("/daily-diaries/{date_str}", response_model=DailyDiaryResponse)
async def update_daily_diary(
    date_str: str,
    payload: DailyDiaryUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    try:
        target_date = _parse_date(date_str)

        content = payload.content.strip()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="content는 비어 있을 수 없습니다.",
            )

        existing = await _get_daily_diary(db, current_user.id, target_date)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 날짜의 하루일기가 존재하지 않습니다.",
            )

        existing.edited_content = content
        existing.edited_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(existing)

        return _serialize_daily_diary(existing)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Daily diary update failed: {e}",
        )


@router.put("/daily-diaries/{date_str}/regenerate", response_model=DailyDiaryResponse)
async def regenerate_daily_diary(
    date_str: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    try:
        target_date = _parse_date(date_str)

        diaries = await _get_one_line_diaries_for_date(db, current_user.id, target_date)
        if not diaries:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 날짜에 한줄일기가 없습니다.",
            )

        one_lines = [diary.content for diary in diaries]

        gen_result = await generate_daily_diary(one_lines)
        full_diary = gen_result["generated_diary"]

        print(
            f"[daily-diary-regenerate] user_id={current_user.id} "
            f"date={target_date} "
            f"model_version={gen_result.get('model_version', 'unknown')} "
            f"one_lines_count={len(one_lines)}",
            flush=True,
        )

        existing = await _get_daily_diary(db, current_user.id, target_date)

        if existing:
            existing.content = full_diary  # 임시 호환용
            existing.generated_content = full_diary
            existing.model_version = gen_result.get("model_version")
            existing.generation_meta = {
                "one_lines_count": gen_result.get("one_lines_count"),
                "bullet_lines": gen_result.get("bullet_lines"),
                "combined_summary": gen_result.get("combined_summary"),
            }
            existing.source_count = len(one_lines)

            # edited_content / edited_at 은 유지
            await db.commit()
            await db.refresh(existing)
            return _serialize_daily_diary(existing)

        new_daily_diary = DailyDiary(
            user_id=current_user.id,
            diary_date=target_date,
            content=full_diary,  # 임시 호환용
            generated_content=full_diary,
            edited_content=None,
            model_version=gen_result.get("model_version"),
            generation_meta={
                "one_lines_count": gen_result.get("one_lines_count"),
                "bullet_lines": gen_result.get("bullet_lines"),
                "combined_summary": gen_result.get("combined_summary"),
            },
            source_count=len(one_lines),
        )
        db.add(new_daily_diary)
        await db.commit()
        await db.refresh(new_daily_diary)

        return _serialize_daily_diary(new_daily_diary)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Daily diary regenerate failed: {e}",
        )