# app/main.py
from dotenv import load_dotenv
load_dotenv()



from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.endpoints import user, diary  # user, diary 라우터 둘 다 임포트

# 앱 인스턴스 생성
app = FastAPI(title="Aiary")

# ---------------- CORS 설정 ----------------
origins = [
    "http://localhost",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:9000",
    "http://10.0.2.2",
    "http://10.0.2.2:8000",
    "http://10.0.2.2:9000",
    "*",  # 개발 단계라 열어두고, 나중에 필요하면 줄이면 됨
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- /media 정적 파일 서빙 ----------------
MEDIA_DIR = Path("media")
IMAGES_DIR = MEDIA_DIR / "images"


@app.on_event("startup")
async def startup_event():
    MEDIA_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)


# /media 로 시작하는 URL은 media 폴더에서 파일 서빙
# 예: http://127.0.0.1:9000/media/images/xxx.jpg
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

# ---------------- 라우터 등록 ----------------
app.include_router(user.router)
app.include_router(diary.router)

# ---------------- 기본 경로 ----------------
@app.get("/")
def read_root():
    return {"message": "안녕하세요! AIary 백엔드 서버입니다."}

# (예시) 일기 생성 API
@app.get("/diary")
def get_diary_example():
    return {"content": "오늘 아기는 정말 잘 웃었다. (AI 생성 예시)"}
