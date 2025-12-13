# app/api/endpoints/diary.py

from datetime import datetime, date, time
from pathlib import Path
from uuid import uuid4
from typing import List

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
    generate_one_line_diary,    # OpenAI Vision + GPT 한 줄 일기
    generate_daily_summary,     # (선택) OpenAI 기반 하루 요약 텍스트
)
from app.services.daily_diary_generator import (
    generate_daily_diary,       # KoBART 하루 줄글 일기 생성
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

# 한 줄 일기를 만들 때 사용할 GPT 프롬프트
GPT_USER_PROMPT = (
    "위 이미지를 보고 오늘 있었던 순간을 떠올리듯이 "
    "아이의 감정, 행동을 파악하고, 주변 사물로 상황을 파악하여 "
    "한국어로 25자 이내의 감성적인 한 줄 일기를 한 문장만 써줘. "
    "문장에 이모지를 적극적으로 활용하세요."
)

# 이미지 저장용 디렉터리 (프로젝트 루트 기준)
MEDIA_DIR = Path("media")
IMAGES_DIR = MEDIA_DIR / "images"
MEDIA_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)


def _generate_filename(original_name: str) -> str:
    """
    업로드된 파일 이름에서 확장자를 유지하면서
    'YYYYMMDD_HHMMSS_랜덤8글자.ext' 형태의 고유한 파일명 생성
    """
    ext = Path(original_name).suffix  # .jpg, .png ...
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    uid = uuid4().hex[:8]
    return f"{ts}_{uid}{ext}"


# 1) 이미지 업로드 + 한 줄 일기 생성

@router.post("/diaries/")
async def create_diary(
    user_id: int = Form(...),        # 프론트에서 넘어오는 user_id (정수)
    photo: UploadFile = File(...),   # multipart/form-data 의 파일 필드
    db: AsyncSession = Depends(get_db_session),
):
    """
    1. 사진 파일을 업로드 받고
    2. OpenAI Vision + GPT로 한 줄 일기를 생성한 뒤
    3. media/images/ 폴더에 이미지를 저장하고
    4. Diary 테이블에 (user_id, content, image_url, created_at)을 저장.

    프론트는 응답으로 넘어오는 `image_url`을 그대로 사용해서
    BASE_URL + image_url 형태로 이미지를 보여줄 수 있다.
    """
    try:
        # 1) 이미지 바이트 읽기
        image_bytes = await photo.read()

        if not image_bytes:
            raise HTTPException(status_code=400, detail="빈 이미지 파일입니다.")

        # 2) GPT로 한 줄 일기 생성
        one_line_diary = await generate_one_line_diary(
            image_bytes,
            GPT_USER_PROMPT,
        )

        # 3) 이미지 파일을 서버 로컬 디스크에 저장
        filename = _generate_filename(photo.filename)
        file_path = IMAGES_DIR / filename
        with open(file_path, "wb") as f:
            f.write(image_bytes)

        # 프론트에서 사용할 이미지 URL (StaticFiles로 /media 마운트되어 있음)
        image_url = f"/media/images/{filename}"

        # 4) DB에 Diary 레코드 저장
        new_diary = Diary(
            user_id=user_id,
            content=one_line_diary,
            image_url=image_url,
            created_at=datetime.utcnow(),
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
            },
        }

    except HTTPException:
        # 우리가 명시적으로 발생시킨 HTTPException은 그대로 전달
        raise
    except Exception as e:
        # 나머지는 500 에러로 감싸서 반환
        raise HTTPException(status_code=500, detail=f"Diary creation failed: {e}")


# 2) 유저별 일기 리스트 조회

@router.get("/diaries/")
async def list_diaries(
    user_id: int,
    db: AsyncSession = Depends(get_db_session),
):
    """
    특정 user_id 의 Diary들을 `created_at` 최신순으로 반환.
    (나중에 페이지네이션이 필요하면 limit/offset 추가 가능)
    """
    try:
        stmt = (
            select(Diary)
            .where(Diary.user_id == user_id)
            .order_by(Diary.created_at.desc())
        )
        result = await db.execute(stmt)
        diaries: List[Diary] = result.scalars().all()

        return [
            {
                "id": d.id,
                "user_id": d.user_id,
                "content": d.content,
                "image_url": d.image_url,  # "/media/images/xxx.jpg"
                "created_at": d.created_at.isoformat(),
            }
            for d in diaries
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diary list failed: {e}")


# 공통: 날짜 문자열을 파싱해서 하루의 시작/끝 datetime으로 바꾸는 헬퍼
def _parse_date_range(date_str: str) -> tuple[datetime, datetime, date]:
    """
    "YYYY-MM-DD" 문자열을 받아서
    - 해당 날짜의 00:00:00 (time.min)
    - 해당 날짜의 23:59:59.999999 (time.max)
    를 반환.
    """
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식은 YYYY-MM-DD 이어야 합니다.")

    start_dt = datetime.combine(target_date, time.min)
    end_dt = datetime.combine(target_date, time.max)
    return start_dt, end_dt, target_date


# 3) 하루 요약 줄글 일기 (OpenAI 기반) - Form 버전

@router.post("/diaries/summary")
async def summarize_diaries_for_day(
    user_id: int = Form(...),
    date_str: str = Form(...),  # 예: "2025-12-09"
    db: AsyncSession = Depends(get_db_session),
):
    """
    - 특정 user_id, 날짜에 해당하는 Diary들의 content를 모아서
    - OpenAI GPT에게 하루 요약 줄글 일기를 생성 요청.
    - 요청은 multipart/form-data (Form 필드) 방식.
    """
    try:
        # 날짜 범위 계산
        start_dt, end_dt, _ = _parse_date_range(date_str)

        # 해당 날짜의 Diary 조회
        stmt = (
            select(Diary)
            .where(Diary.user_id == user_id)
            .where(Diary.created_at >= start_dt)
            .where(Diary.created_at <= end_dt)
            .order_by(Diary.created_at.asc())
        )
        result = await db.execute(stmt)
        diaries: List[Diary] = result.scalars().all()

        if not diaries:
            raise HTTPException(status_code=404, detail="해당 날짜에 일기가 없습니다.")

        one_lines = [d.content for d in diaries]

        # OpenAI GPT 기반 요약 (옵션 기능)
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


# 4) 하루 요약 줄글 일기 (OpenAI 기반) - JSON 버전

@router.post("/diaries/summary-json")
async def summarize_diaries_for_day_json(
    payload: DaySummaryRequest,              # JSON Body 전체를 한 번에 받음
    db: AsyncSession = Depends(get_db_session),
):
    """
    JSON Body 예시:
        {
          "user_id": 1,
          "date": "2025-12-09"
        }

    동작은 /diaries/summary 와 동일하지만
    content-type 이 application/json 인 버전.
    (안드로이드에서 Retrofit @Body 로 보내기 편함)
    """
    try:
        user_id = payload.user_id
        date_str = payload.date

        # 날짜 범위 계산
        start_dt, end_dt, _ = _parse_date_range(date_str)

        # 해당 날짜의 Diary 조회
        stmt = (
            select(Diary)
            .where(Diary.user_id == user_id)
            .where(Diary.created_at >= start_dt)
            .where(Diary.created_at <= end_dt)
            .order_by(Diary.created_at.asc())
        )
        result = await db.execute(stmt)
        diaries: List[Diary] = result.scalars().all()

        if not diaries:
            raise HTTPException(status_code=404, detail="해당 날짜에 일기가 없습니다.")

        one_lines = [d.content for d in diaries]

        # OpenAI GPT 기반 요약 (옵션 기능)
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


# 5) 하루 "줄글 일기" (KoBART 학습 모델) 생성 - JSON 버전

@router.post("/diaries/full")
async def create_full_daily_diary(
    payload: DaySummaryRequest,              # { "user_id": 1, "date": "2025-12-09" }
    db: AsyncSession = Depends(get_db_session),
):
    """
    ✅ 이 엔드포인트가 **KoBART 학습 모델**을 사용하는 핵심 API.

    동작:
      1) 특정 user_id + date 에 해당하는 Diary.content(한 줄 일기)들을 전부 모음
      2) daily_diary_generator.generate_daily_diary() 호출
         - 내부에서:
           - 한 줄 일기들을 클린업
           - "1. ~" 리스트(bullet_lines) + combined_summary를 만들고
           - KoBART 모델로 줄글 하루 일기 생성
      3) bullet_lines / combined_summary / generated_diary 를 함께 반환

    요청 JSON 예시:
        {
          "user_id": 1,
          "date": "2025-12-09"
        }
    """
    try:
        user_id = payload.user_id
        date_str = payload.date

        # 날짜 범위 계산
        start_dt, end_dt, _ = _parse_date_range(date_str)

        # 해당 날짜의 Diary 조회
        stmt = (
            select(Diary)
            .where(Diary.user_id == user_id)
            .where(Diary.created_at >= start_dt)
            .where(Diary.created_at <= end_dt)
            .order_by(Diary.created_at.asc())
        )
        result = await db.execute(stmt)
        diaries: List[Diary] = result.scalars().all()

        if not diaries:
            raise HTTPException(status_code=404, detail="해당 날짜에 일기가 없습니다.")

        # 한 줄 일기 텍스트만 추출
        one_lines = [d.content for d in diaries]

        # KoBART 하루 줄글 일기 생성 (heavy 연산은 daily_diary_generator 내부에서 thread pool로 실행)
        gen_result = await generate_daily_diary(one_lines)

        return {
            "status": "success",
            "user_id": user_id,
            "date": date_str,
            # 모델이 사용한 중간 요약 정보들
            "bullet_lines": gen_result["bullet_lines"],           # ["1. ...", "2. ...", ...]
            "combined_summary": gen_result["combined_summary"],   # bullet들을 합친 문자열
            # 최종 줄글 하루 일기
            "full_diary": gen_result["generated_diary"],
            # 원본 한 줄 일기 개수
            "source_count": len(one_lines),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Daily diary generation failed: {e}")
