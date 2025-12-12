 Aiary Backend (FastAPI)

FastAPI 기반으로 작성된 Aiary의 서버 애플리케이션입니다.

📂 Backend 구조
backend/
│
├── app/
│   ├── api/endpoints/        # diary, user 관련 API 라우터
│   ├── db/                   # DB model / 연결
│   ├── schemas/              # Pydantic 요청/응답 모델
│   ├── services/             # GPT·KoBART 호출 / 일기 생성 로직
│   └── config.py             # 환경 변수 로딩
│
├── media/images/             # 업로드된 이미지 저장
├── models/                   # (실행용) 모델 가중치 폴더 (별도 다운로드)
│
├── .env.example              # 환경 변수 템플릿
├── Dockerfile
├── create_tables.py
└── main.py                   # 서버 시작점

 환경변수(.env 설정)

프로젝트 루트에 아래와 같은 .env 파일이 필요합니다:

OPENAI_API_KEY=YOUR_KEY
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/aiary_db


.env.example 참고하면 됩니다.

 .env는 절대 Git에 올리지 않습니다.

 백엔드 실행 방법
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
uvicorn main:app --reload


Swagger 문서:
 http://127.0.0.1:8000/docs

 AI 모델 경로

FastAPI는 내부에서 다음 경로로부터 모델을 사용합니다:

backend/models/day_diary_from_summary_v2/
backend/models/one_line_diary/


모델 파일들은 GitHub에 포함되어 있지 않고,
models/README.md 안내에 따라 다운로드 후 위 경로에 넣어야 합니다.
