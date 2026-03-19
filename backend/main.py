from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.endpoints import user, diary, export, report
from app.config import settings

# 🌟 [추가됨] 비전 AI 모델 로드 함수 가져오기
from app.services.vision_analyzer import load_vision_models

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
    # 1. 미디어 폴더 생성
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    # 🌟 2. [핵심 추가] 서버 켜질 때 비전 AI 모델 미리 메모리에 올려두기!
    print("🚀 [System] 서버 부팅 중: AI 모델을 메모리에 적재합니다...")
    load_vision_models()
    print("✅ [System] AI 모델 적재 완료! 서버가 정상적으로 응답을 시작합니다.")


app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

# 라우터 등록
app.include_router(user.router)
app.include_router(diary.router)
app.include_router(export.router)
app.include_router(report.router, prefix="/report", tags=["Report"])


@app.get("/")
def read_root():
    return {"message": "안녕하세요! AIary 백엔드 서버입니다."}


@app.get("/diary")
def get_diary_example():
    return {"content": "오늘 아기는 정말 잘 웃었다. (AI 생성 예시)"}