# app/services/storage.py

from __future__ import annotations

from datetime import date as DateType
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, status

from app.config import settings


_ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/octet-stream",
}


def validate_image_upload(filename: str, content_type: Optional[str]) -> str:
    ext = Path(filename or "").suffix.lower() or ".jpg"

    if ext == ".jpeg":
        ext = ".jpg"

    if ext not in _ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="지원하지 않는 이미지 확장자입니다. jpg, png, webp만 업로드할 수 있습니다.",
        )

    if content_type and content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="지원하지 않는 이미지 MIME 타입입니다.",
        )

    return ext


def generate_image_filename(ext: str) -> str:
    if not ext.startswith("."):
        ext = "." + ext

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    uid = uuid4().hex[:8]
    return f"{ts}_{uid}{ext}"


def build_s3_key(user_id: int, filename: str, diary_date: Optional[DateType] = None) -> str:
    prefix = settings.AWS_S3_PREFIX.strip("/")

    if diary_date:
        year = f"{diary_date.year:04d}"
        month = f"{diary_date.month:02d}"
    else:
        now = datetime.utcnow()
        year = f"{now.year:04d}"
        month = f"{now.month:02d}"

    key = f"{user_id}/diaries/{year}/{month}/{filename}"

    if prefix:
        return f"{prefix}/{key}"

    return key


def build_s3_url(s3_key: str) -> str:
    base = settings.AWS_S3_PUBLIC_BASE_URL.strip().rstrip("/")

    if base:
        return f"{base}/{s3_key}"

    # private bucket 구조에서는 이 URL이 직접 열리지 않을 수 있음.
    # DB에는 참조용으로 저장하고, 추후 presigned URL API로 확장 가능.
    return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"


def upload_image_to_s3(
    *,
    image_bytes: bytes,
    user_id: int,
    filename: str,
    content_type: Optional[str],
    diary_date: Optional[DateType] = None,
) -> dict:
    if not settings.AWS_S3_BUCKET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AWS_S3_BUCKET 설정이 없습니다.",
        )

    s3_key = build_s3_key(
        user_id=user_id,
        filename=filename,
        diary_date=diary_date,
    )

    s3 = boto3.client("s3", region_name=settings.AWS_REGION)

    try:
        s3.put_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=s3_key,
            Body=image_bytes,
            ContentType=content_type or "image/jpeg",
        )
    except (BotoCoreError, ClientError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"S3 이미지 업로드 실패: {e}",
        )

    return {
        "image_url": build_s3_url(s3_key),
        "image_storage": "s3",
        "image_key": s3_key,
        "image_filename": filename,
    }


def save_image_locally(
    *,
    image_bytes: bytes,
    filename: str,
) -> dict:
    images_dir = Path(settings.IMAGE_UPLOAD_DIR)
    images_dir.mkdir(parents=True, exist_ok=True)

    file_path = images_dir / filename

    with open(file_path, "wb") as f:
        f.write(image_bytes)

    return {
        "image_url": f"/media/images/{filename}",
        "image_storage": "local",
        "image_key": None,
        "image_filename": filename,
    }


def save_uploaded_image(
    *,
    image_bytes: bytes,
    user_id: int,
    original_filename: str,
    content_type: Optional[str],
    diary_date: Optional[DateType] = None,
) -> dict:
    ext = validate_image_upload(original_filename, content_type)
    filename = generate_image_filename(ext)

    if settings.STORAGE_BACKEND.lower() == "s3":
        return upload_image_to_s3(
            image_bytes=image_bytes,
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            diary_date=diary_date,
        )

    return save_image_locally(
        image_bytes=image_bytes,
        filename=filename,
    )
    
def generate_presigned_image_url(
    *,
    image_storage: str | None,
    image_key: str | None,
    image_url: str | None,
    expires_in: int = 3600,
) -> str | None:
    if not image_url:
        return None
    if image_storage == "s3" and image_key:
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        return s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": settings.AWS_S3_BUCKET,
                "Key": image_key,
            },
            ExpiresIn=expires_in,
        )
    return image_url

