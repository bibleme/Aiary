# backend/app/api/endpoints/diary.py

from datetime import datetime, date, time
from pathlib import Path
from uuid import uuid4
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form,
    HTTPException,
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db_session
from app.db.model import Diary
from app.services.ai_generator import (
    generate_one_line_diary,   # OpenAI Vision + GPT 한 줄 일기
    generate_daily_summary,    # (선택) OpenAI 기반 하루 요약 텍스트
)
from app.services.daily_diary_generator import (
    generate_daily_diary,      # KoBART 하루 줄글 일기 생성
)

router = APIRouter(tags=["diaries"])

# ---------- 공통으로 쓸 Pydantic 모델 ----------
class DaySummaryRequest(BaseModel):
    """
    하루 요약/줄글 일기를 생성할 때 공통으로 사용하는 요청 바디 형태.
    - user_id: 어떤 유저의 일기인지
    - date: "YYYY-MM-DD" 형식의 날짜 문자열
    """
    user_id: int
    date: str

# ---------- 공통 상수 / 디렉터리 설정 ----------
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

def _generate_filename(original_name: str) -> str:
    ext = Path(original_name).suffix
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    uid = uuid4().hex[:8]
    return f"{ts}_{uid}{ext}"

def _parse_date_range(date_str: str) -> tuple[datetime, datetime, date]:
    """
    "YYYY-MM-DD" 문자열을 받아서
    - 해당 날짜의 00:00:00
    - 해당 날짜의 23:59:59.999999
    를 반환.
    """
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식은 YYYY-MM-DD 이어야 합니다.")
    start_dt = datetime.combine(target_date, time.min)
    end_dt = datetime.combine(target_date, time.max)
    return start_dt, end_dt, target_date


# 1) 이미지 업로드 + 한 줄 일기 생성 (+ ✅ date 저장)
@router.post("/diaries/")
async def create_diary(
    user_id: int = Form(...),
    photo: UploadFile = File(...),
    # ✅ 프론트 요청사항: date도 받기 (없어도 오늘로 저장되어 안 터지게)
    date_str: Optional[str] = Form(None),   # 프론트에서 "date" 키로 보내면 여기에 들어옴
    db: AsyncSession = Depends(get_db_session),
):
    """
    1. 사진 파일을 업로드 받고
    2. OpenAI Vision + GPT로 한 줄 일기를 생성한 뒤
    3. media/images/ 폴더에 이미지를 저장하고
    4. Diary 테이블에 (user_id, content, image_url, created_at, diary_date)을 저장
    """
    try:
        # ✅ date 파싱 (없으면 오늘)
        if date_str:
            try:
                diary_date = date.fromisoformat(date_str)
            except ValueError:
                raise HTTPException(status_code=400, detail="date는 YYYY-MM-DD 형식이어야 합니다.")
        else:
            diary_date = date.today()

        # 1) 이미지 바이트 읽기
        image_bytes = await photo.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="빈 이미지 파일입니다.")

        # 2) GPT로 한 줄 일기 생성
        one_line_diary = await generate_one_line_diary(
            image_bytes,
            GPT_USER_PROMPT,
        )

        # 3) 이미지 파일 저장
        filename = _generate_filename(photo.filename)
        file_path = IMAGES_DIR / filename
        with open(file_path, "wb") as f:
            f.write(image_bytes)

        image_url = f"/media/images/{filename}"

        # 4) DB 저장 (✅ diary_date 포함)
        new_diary = Diary(
            user_id=user_id,
            content=one_line_diary,
            image_url=image_url,
            created_at=datetime.utcnow(),
            diary_date=diary_date,
        )
        db.add(new_diary)
        await db.commit()
        await db.refresh(new_diary)

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


# 2) 유저별 일기 리스트 조회 (✅ 옵션: date로 필터 가능)
@router.get("/diaries/")
async def list_diaries(
    user_id: int,
    date_str: Optional[str] = None,  # ?date_str=YYYY-MM-DD 를 주면 그 날짜만
    db: AsyncSession = Depends(get_db_session),
):
    """
    특정 user_id 의 Diary들을 반환.
    - date_str이 있으면 diary_date 기준으로 필터링
    - 없으면 전체를 created_at 최신순으로
    """
    try:
        stmt = select(Diary).where(Diary.user_id == user_id)

        if date_str:
            _, _, target_date = _parse_date_range(date_str)
            stmt = stmt.where(Diary.diary_date == target_date)

        stmt = stmt.order_by(Diary.created_at.desc())

        result = await db.execute(stmt)
        diaries: List[Diary] = result.scalars().all()

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


# 3) 하루 요약 (OpenAI) - Form
@router.post("/diaries/summary")
async def summarize_diaries_for_day(
    user_id: int = Form(...),
    date_str: str = Form(...),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        _, _, target_date = _parse_date_range(date_str)

        # ✅ diary_date 기준으로 조회 (date 도입했으니 이게 정확)
        stmt = (
            select(Diary)
            .where(Diary.user_id == user_id)
            .where(Diary.diary_date == target_date)
            .order_by(Diary.created_at.asc())
        )
        result = await db.execute(stmt)
        diaries: List[Diary] = result.scalars().all()

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
        raise HTTPException(status_code=500, detail=f"Diary summary failed: {e}")


# 4) 하루 요약 (OpenAI) - JSON
@router.post("/diaries/summary-json")
async def summarize_diaries_for_day_json(
    payload: DaySummaryRequest,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        user_id = payload.user_id
        date_str = payload.date
        _, _, target_date = _parse_date_range(date_str)

        stmt = (
            select(Diary)
            .where(Diary.user_id == user_id)
            .where(Diary.diary_date == target_date)
            .order_by(Diary.created_at.asc())
        )
        result = await db.execute(stmt)
        diaries: List[Diary] = result.scalars().all()

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


# 5) 하루 "줄글 일기" (KoBART) - JSON
@router.post("/diaries/full")
async def create_full_daily_diary(
    payload: DaySummaryRequest,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        user_id = payload.user_id
        date_str = payload.date
        _, _, target_date = _parse_date_range(date_str)

        stmt = (
            select(Diary)
            .where(Diary.user_id == user_id)
            .where(Diary.diary_date == target_date)
            .order_by(Diary.created_at.asc())
        )
        result = await db.execute(stmt)
        diaries: List[Diary] = result.scalars().all()

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


# ✅ 6) 삭제 API (일기 + 이미지 파일 삭제)
@router.delete("/diaries/{diary_id}")
async def delete_diary(
    diary_id: int,
    user_id: int,  # 인증 토큰이 없으니 임시로 query param으로 받음: /diaries/123?user_id=1
    db: AsyncSession = Depends(get_db_session),
):
    try:
        # 1) 일기 조회
        stmt = select(Diary).where(Diary.id == diary_id)
        result = await db.execute(stmt)
        diary: Diary | None = result.scalar_one_or_none()

        if diary is None:
            raise HTTPException(status_code=404, detail="해당 일기가 존재하지 않습니다.")

        # 2) 본인 글인지 확인
        if diary.user_id != user_id:
            raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")

        # 3) 이미지 파일 삭제 시도 (실패해도 DB 삭제는 진행)
        try:
            # diary.image_url = "/media/images/xxx.jpg"
            if diary.image_url and diary.image_url.startswith("/media/images/"):
                filename = diary.image_url.split("/")[-1]
                file_path = IMAGES_DIR / filename
                if file_path.exists():
                    file_path.unlink()
        except Exception:
            pass

        # 4) DB 삭제
        await db.delete(diary)
        await db.commit()

        return {"status": "success", "deleted_diary_id": diary_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diary delete failed: {e}")
