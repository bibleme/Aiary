# app/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DATABASE_URL: str
    IMAGE_UPLOAD_DIR: str
    DAILY_DIARY_MODEL_DIR: str
    DAILY_DIARY_RUNTIME_VERSION: str = "realistic_daily"

    OPENAI_API_KEY: str = ""
    PUBLIC_BASE_URL: str = "http://3.35.185.251:8000"

    MONTHLY_REPORT_JSON_PATH: str = "/home/ubuntu/aiary-assets/reports/monthly/v3/monthly_reports_v3.json"
    MONTHLY_REPORT_SCENE_CACHE_PATH: str = "/home/ubuntu/aiary-assets/reports/monthly/v3/scene_extraction_results_v3.json"
    MONTHLY_REPORT_MIN_DIARIES: int = 5
    MONTHLY_REPORT_USE_JSON_FALLBACK: bool = True
    MONTHLY_REPORT_USE_GPT_SCENE: bool = True
    MONTHLY_REPORT_USE_GPT_REPORT: bool = True
    MONTHLY_REPORT_OPENAI_MODEL: str = "gpt-4.1-mini"
    MONTHLY_REPORT_SCENE_OPENAI_MODEL: str = "gpt-4.1-mini"

    # CV settings
    CV_ENABLED: bool = True
    CV_MODELS_ROOT: str = "/home/ubuntu/aiary-assets/cv/models"
    CV_CHILD_REFS_ROOT: str = "/home/ubuntu/aiary-assets/cv/child_refs"
    CV_CACHE_ROOT: str = "/home/ubuntu/aiary-assets/cv/cache"
    CV_LOG_ROOT: str = "/home/ubuntu/aiary-assets/cv/logs"
    CV_DEBUG_ROOT: str = "/home/ubuntu/aiary-assets/cv/debug"
    CV_TEMP_ROOT: str = "/home/ubuntu/aiary-assets/cv/temp"

    CV_YOLO_OBJECT_MODEL: str = "/home/ubuntu/aiary-assets/cv/models/yolo26m.pt"
    CV_YOLO_POSE_MODEL: str = "/home/ubuntu/aiary-assets/cv/models/yolo26m-pose.pt"

    CV_CLIP_MODEL_NAME: str = "ViT-B/32"
    CV_SIGLIP_MODEL_NAME: str = "google/siglip-base-patch16-224"

    CV_SIMILARITY_THRESHOLD: float = 0.75
    CV_SCENE_CLUSTER_THRESHOLD: float = 0.88
    CV_TARGET_CHILD_VERIFY_THRESHOLD: float = 0.35
    CV_BATCH_LIMIT: int = 20
    
    CV_LOAD_POSE_MODEL: bool = False
    CV_USE_SIGLIP_EMBEDDINGS: bool = False
    CV_WORKER_BATCH_LIMIT: int = 1
    
    STORAGE_BACKEND: str = "s3"
    AWS_REGION: str = "ap-northeast-2"
    AWS_S3_BUCKET: str = ""
    AWS_S3_PREFIX: str = "users"
    AWS_S3_PUBLIC_BASE_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()