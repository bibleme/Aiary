# backend/app/api/endpoints/diary.py

from datetime import date, datetime
from pathlib import Path
from uuid import uuid4
from typing import Optional, List

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.db import crud
from app.services.ai_generator import generate_one_line_diary, generate_daily_summary
from app.services.daily_diary_generator import generate_daily_diary

router = APIRouter(tags=["diaries"])

GPT_USER_PROMPT = (
    "위 이미지를 보고 오늘 있었던 순간을 떠올리듯이 "
    "아이의 감정, 행동을 파악하고, 주변 사물로 상황을 파악하여 "
    "한국어로 25자 이내의 감성적인 한 줄 일기를 한 문장만 써줘. "
    "문장에 이모지를 적극적으로 활용하세요."
)

MEDIA_DIR = Path("media")
IMAGES_DIR = MEDIA_DIR / "images"
MEDIA_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)


class DaySummaryRequest(BaseModel):
    user_id: int
    date: str  # "YYYY-MM-DD"


def _parse_date(date_str: str) -> date:
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="date는 YYYY-MM-DD 형식이어야 합니다.")


def _generate_filename(original_name: str) -> str:
    ext = Path(original_name).suffix
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    uid = uuid4().hex[:8]
    return f"{ts}_{uid}{ext}"


@router.post("/diaries/")
async def create_diary(
    user_id: int = Form(...),
    photo: UploadFile = File(...),
    # ✅ 프론트가 date를 보내면 여기로(키 이름은 date로 맞추는 걸 추천)
    date: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        diary_date = _parse_date(date) if date else date_today()

        image_bytes = await photo.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="빈 이미지 파일입니다.")

        one_line = await generate_one_line_diary(image_bytes, GPT_USER_PROMPT)

        filename = _generate_filename(photo.filename)
        file_path = IMAGES_DIR / filename
        with open(file_path, "wb") as f:
            f.write(image_bytes)

        image_url = f"/media/images/{filename}"

        new_diary = await crud.create_diary(
            db=db,
            user_id=user_id,
            content=one_line,
            image_url=image_url,
            diary_date=diary_date,
        )

        return {
            "status": "success",
            "diary": {
                "id": new_diary.id,
                "user_id": new_diary.user_id,
                "content": new_diary.content,
                "image_url": new_diary.image_url,
                "created_at": new_diary.created_at.isoformat(),
                "diary_date": new_diary.diary_date.isoformat(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diary creation failed: {e}")


def date_today() -> date:
    return date.today()


@router.get("/diaries/")
async def list_diaries(
    user_id: int,
    date: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        diary_date = _parse_date(date) if date else None
        diaries = await crud.list_diaries_by_user(db, user_id=user_id, diary_date=diary_date)

        return [
            {
                "id": d.id,
                "user_id": d.user_id,
                "content": d.content,
                "image_url": d.image_url,
                "created_at": d.created_at.isoformat(),
                "diary_date": d.diary_date.isoformat(),
            }
            for d in diaries
        ]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diary list failed: {e}")


@router.post("/diaries/summary")
async def summary_form(
    user_id: int = Form(...),
    date: str = Form(...),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        target_date = _parse_date(date)
        diaries = await crud.list_diaries_by_user(db, user_id=user_id, diary_date=target_date)
        if not diaries:
            raise HTTPException(status_code=404, detail="해당 날짜에 일기가 없습니다.")

        one_lines = [d.content for d in diaries]
        summary = await generate_daily_summary(one_lines, date)

        return {
            "status": "success",
            "user_id": user_id,
            "date": date,
            "summary": summary,
            "source_count": len(one_lines),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diary summary failed: {e}")


@router.post("/diaries/summary-json")
async def summary_json(
    payload: DaySummaryRequest,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        user_id = payload.user_id
        date_str = payload.date
        target_date = _parse_date(date_str)

        diaries = await crud.list_diaries_by_user(db, user_id=user_id, diary_date=target_date)
        if not diaries:
            raise HTTPException(status_code=404, detail="해당 날짜에 일기가 없습니다.")

        one_lines = [d.content for d in diaries]
        summary = await generate_daily_summary(one_lines, date_str)

        return {
            "status": "success",
            "user_id": user_id,
            "date": date_str,
            "summary": summary,
            "source_count": len(one_lines),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diary summary (json) failed: {e}")


@router.post("/diaries/full")
async def full_daily_diary(
    payload: DaySummaryRequest,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        user_id = payload.user_id
        date_str = payload.date
        target_date = _parse_date(date_str)

        diaries = await crud.list_diaries_by_user(db, user_id=user_id, diary_date=target_date)
        if not diaries:
            raise HTTPException(status_code=404, detail="해당 날짜에 일기가 없습니다.")

        one_lines = [d.content for d in diaries]
        gen_result = await generate_daily_diary(one_lines)

        return {
            "status": "success",
            "user_id": user_id,
            "date": date_str,
            "bullet_lines": gen_result["bullet_lines"],
            "combined_summary": gen_result["combined_summary"],
            "full_diary": gen_result["generated_diary"],
            "source_count": len(one_lines),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Daily diary generation failed: {e}")


@router.delete("/diaries/{diary_id}")
async def delete_diary(
    diary_id: int,
    user_id: int,  # 임시: 인증 토큰 없어서 query로 받기 /diaries/1?user_id=1
    db: AsyncSession = Depends(get_db_session),
):
    try:
        result = await crud.delete_diary(db, diary_id=diary_id, user_id=user_id)
        if result is None:
            raise HTTPException(status_code=404, detail="해당 일기가 존재하지 않습니다.")
        if result is False:
            raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")
        return {"status": "success", "deleted_diary_id": diary_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diary delete failed: {e}")
