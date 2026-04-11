# main.py
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.endpoints import user, diary, export, monthly_report, cv
from app.config import settings
from app.db.database import engine
from app.db.model import Base

app = FastAPI(title="Aiary")

origins = [
    "http://localhost",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:9000",
    "http://10.0.2.2",
    "http://10.0.2.2:8000",
    "http://10.0.2.2:9000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

IMAGES_DIR = Path(settings.IMAGE_UPLOAD_DIR)
MEDIA_DIR = IMAGES_DIR.parent


@app.on_event("startup")
async def startup_event():
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

app.include_router(user.router)
app.include_router(diary.router)
app.include_router(export.router)
app.include_router(monthly_report.router)
app.include_router(cv.router)


@app.get("/")
def read_root():
    return {"message": "안녕하세요! AIary 백엔드 서버입니다."}


@app.get("/diary")
def get_diary_example():
    return {"content": "오늘 아기는 정말 잘 웃었다. (AI 생성 예시)"}