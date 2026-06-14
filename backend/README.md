
---

# 📡 **Aiary Backend – FastAPI 서비스**

이 서버는 **사진 업로드 → AI 한 줄 일기 생성 → DB 저장 → 하루 요약 줄글 생성 → KoBART 줄글 일기 생성**의 모든 백엔드 로직을 담당합니다.

---

## 📂 폴더 구조

```
backend/
│
├── app/
│   ├── api/endpoints/              # API 라우터 (엔드포인트)
│   │   ├── diary.py                # 일기 관련 API
│   │   ├── export.py               # 내보내기 관련 API
│   │   ├── report.py               # 리포트 관련 API
│   │   └── user.py                 # 유저(인증/가입) 관련 API
│   │
│   ├── db/                         # 데이터베이스 설정 및 관리
│   │   ├── __init__.py
│   │   ├── crud.py                 # DB 데이터 조작 (Create, Read, Update, Delete)
│   │   ├── database.py             # DB 연결 세션 관리
│   │   └── model.py                # SQLModel (테이블 스키마)
│   │
│   ├── schemas/                    # Pydantic 데이터 검증 모델 (Request/Response)
│   │   ├── diary.py
│   │   ├── export.py
│   │   └── user.py
│   │
│   ├── services/                   # 핵심 비즈니스 로직 및 AI 파이프라인
│   │   ├── __init__.py
│   │   ├── ai_generator.py                  # AI 텍스트 생성 관련 서비스
│   │   ├── daily_diary_generator_v3.py      # 고도화된 최신 하루 일기 생성 모델
│   │   ├── daily_diary_generator_v3_eval.py # 일기 생성 모델 평가 로직
│   │   ├── report_generator.py              # 월간 리포트 및 통계 생성
│   │   ├── security.py                      # 비밀번호 해싱 및 JWT 토큰 보안 로직
│   │   └── vision_analyzer.py               # 컴퓨터 비전(CV) 객체/감정 분석 로직
│   │
│   └── config.py                   # 환경 변수 및 서버 설정 관리
│
├── media/images/                   # CV 타겟 인식용 기준 사진 및 로컬 테스트 이미지
│   ├── my_child_ref.jpg
│   ├── ref_2026-04.jpg
│   └── test_image2.jpg
│
├── scripts/                        # 배치 작업 및 자동화 스크립트 폴더
│
├── Dockerfile                      # 도커 컨테이너 빌드 설정 파일
├── README.md                       # 백엔드 프로젝트 설명서
├── create_tables.py                # 초기 DB 테이블 생성 스크립트
├── main.py                         # FastAPI 애플리케이션 실행 엔트리포인트 (uvicorn)
└── requirements.txt                # 파이썬 필수 의존성 패키지 목록
```

---

## 🔐 환경 변수(.env)

`.env.example`을 복사하여 `.env`를 생성:

```
OPENAI_API_KEY=YOUR_KEY
DATABASE_URL=postgresql+asyncpg://aiary_user:aiary_pass@localhost:5432/aiary_db
```

---

## 🚀 서버 실행

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Swagger 문서 → [[http://127.0.0.1:8000/docs](http://3.35.185.251:8000/docs)]

---

## 🎯 제공 API 요약

### 📌 1) 사진 업로드 + 한 줄 일기 생성

```
POST /diaries/
form-data:
  user_id: int
  photo: 이미지 파일
```

GPT Vision → 한 줄 일기 생성 후 DB 저장

---

### 📌 2) 유저별 일기 리스트

```
GET /diaries/?user_id=1
```

---

### 📌 3) 하루 줄글 요약(GPT 기반)

```
POST /diaries/summary
```

---

### 📌 4) 하루 줄글 요약(JSON 버전)

```
POST /diaries/summary-json
```

---

### 📌 5) 줄글 일기 생성(KoBART 학습 모델)

`daily_diary_generator.py` 내부에서 호출됨.
`summary_text` → 모델 입력 → 줄글 일기 생성.

---

## 🤖 KoBART 모델 배치

Google Drive 모델 다운로드 →
👉 [https://drive.google.com/drive/folders/1bZPq1JaPhUTS6As8tW0tvMUuIcHYiIXl](https://drive.google.com/drive/folders/1bZPq1JaPhUTS6As8tW0tvMUuIcHYiIXl)

아래에 저장:

```
backend/models/day_diary_from_summary_v2/
```

https://github.com/subin0910/Aiary-backend/issues/1#issue-4658088999
