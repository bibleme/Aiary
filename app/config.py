# app/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    

    DATABASE_URL: str

    IMAGE_UPLOAD_DIR: str
    DAILY_DIARY_MODEL_DIR: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )
    
    OPENAI_API_KEY: str = ""
    PUBLIC_BASE_URL: str = "http://3.35.185.251:8000"

    MONTHLY_REPORT_JSON_PATH: str = "/home/ubuntu/aiary-assets/reports/monthly/v3/monthly_reports_v3.json"
    MONTHLY_REPORT_SCENE_CACHE_PATH: str = "/home/ubuntu/aiary-assets/reports/monthly/v3/scene_extraction_results_v3.json"
    MONTHLY_REPORT_MIN_DIARIES: int = 5

    MONTHLY_REPORT_USE_JSON_FALLBACK: bool = True

    MONTHLY_REPORT_USE_GPT_SCENE: bool = False
    MONTHLY_REPORT_USE_GPT_REPORT: bool = False
    MONTHLY_REPORT_OPENAI_MODEL: str = "gpt-4.1-mini"
    MONTHLY_REPORT_SCENE_OPENAI_MODEL: str = "gpt-4.1-mini"


settings = Settings()
