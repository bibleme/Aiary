# app/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from datetime import timedelta

class Settings(BaseSettings):
    # JWT 암호화에 사용할 Secret Key (반드시 변경하세요!)
    SECRET_KEY: str = "Gachon University"
    ALGORITHM: str = "HS256"
    # 토큰 만료 시간 (예: 60분)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # DB 연결 정보 (database.py에서 os.getenv로 불러오는 것과 일치)
    DATABASE_URL: str = "postgresql+asyncpg://user:password@aiary-db:5432/aiary"

    # 설정 로딩 방식 지정 (env 파일에서 로드)
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

settings = Settings()