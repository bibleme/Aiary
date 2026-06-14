
---

# 📡 **Aiary Backend – FastAPI 서비스**

이 서버는 **사진 업로드 → AI 한 줄 일기 생성 → DB 저장 → 하루 요약 줄글 생성 → KoBART 줄글 일기 생성**의 모든 백엔드 로직을 담당합니다.

---

## 📂 폴더 구조

```
backend/
│
├── app/
│   ├── api/endpoints/
│   │   ├── user.py
│   │   ├── diary.py
│   ├── db/
│   │   ├── database.py
│   │   ├── model.py
│   ├── services/
│       ├── ai_generator.py             # GPT Vision + 요약
│       ├── daily_diary_generator.py    # KoBART 줄글 일기 모델
│
├── media/images/                       # 업로드 이미지 저장
│
├── models/                             # KoBART 모델 위치
│
├── create_tables.py
├── requirements.txt
├── .env.example
└── main.py
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

Swagger 문서 → [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

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
