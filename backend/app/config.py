import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# 현재 파일 위치 기준 상위 폴더(backend)의 .env 경로 계산
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DATABASE_URL: str

    IMAGE_UPLOAD_DIR: str
    DAILY_DIARY_MODEL_DIR: str

    # 🌟 수정 포인트: 따옴표를 제거하고 변수명을 그대로 넣어야 합니다.
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH), # 문자열이 아닌 변수를 넣음
        env_file_encoding='utf-8',
        extra="ignore",
    )

# 실행 전 .env 파일이 있는지 터미널에 출력해주는 디버깅 코드 (선택 사항)
if not ENV_FILE_PATH.exists():
    print(f"⚠️ 경고: .env 파일을 찾을 수 없습니다! 위치 확인 필요: {ENV_FILE_PATH}")

settings = Settings()