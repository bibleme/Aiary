# app/services/image_resolver.py

from __future__ import annotations

import tempfile
from pathlib import Path
from urllib.parse import urlparse

import boto3
import requests

from app.config import settings


def is_remote_url(image_url: str) -> bool:
    return image_url.startswith("http://") or image_url.startswith("https://")


def download_s3_key_to_temp(image_key: str) -> str:
    temp_root = Path(settings.CV_TEMP_ROOT)
    temp_root.mkdir(parents=True, exist_ok=True)

    suffix = Path(image_key).suffix or ".jpg"
    tmp = tempfile.NamedTemporaryFile(
        suffix=suffix,
        dir=str(temp_root),
        delete=False,
    )
    tmp.close()

    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    s3.download_file(settings.AWS_S3_BUCKET, image_key, tmp.name)

    return tmp.name


def download_remote_url_to_temp(image_url: str) -> str:
    temp_root = Path(settings.CV_TEMP_ROOT)
    temp_root.mkdir(parents=True, exist_ok=True)

    parsed = urlparse(image_url)
    suffix = Path(parsed.path).suffix or ".jpg"

    response = requests.get(
    image_url,
    timeout=(5, 30),
    allow_redirects=True,
    )
    response.raise_for_status()

    tmp = tempfile.NamedTemporaryFile(
        suffix=suffix,
        dir=str(temp_root),
        delete=False,
    )
    tmp.write(response.content)
    tmp.flush()
    tmp.close()

    return tmp.name


def resolve_image_path_for_cv(
    *,
    image_url: str,
    image_storage: str = "local",
    image_key: str | None = None,
) -> tuple[Path, bool]:
    if image_storage == "s3" and image_key:
        return Path(download_s3_key_to_temp(image_key)), True

    if image_url.startswith("/media/images/"):
        filename = image_url.split("/")[-1]
        return Path(settings.IMAGE_UPLOAD_DIR) / filename, False

    if image_url.startswith("/media/"):
        media_relative = image_url.split("/media/", 1)[1]
        media_root = Path(settings.IMAGE_UPLOAD_DIR).parent
        return media_root / media_relative, False

    if is_remote_url(image_url):
        return Path(download_remote_url_to_temp(image_url)), True

    return Path(image_url), False


def cleanup_temp_image(path: Path, is_temp: bool) -> None:
    if not is_temp:
        return

    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass
