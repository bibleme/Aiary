🌿 Aiary – AI 기반 사진 자동 일기 생성 서비스

Aiary는 아기의 사진을 올리면 자동으로 한 줄 일기와 하루 줄글 일기를 생성해주는 AI 서비스입니다.

사진 → 한 줄 일기 (GPT Vision 기반)

여러 한 줄 일기 → 하루 요약 줄글 일기 (KoBART fine-tuned 모델 기반)

FastAPI 백엔드 + Android 프론트 + 맞춤형 KoBART 모델이 하나의 프로젝트로 통합된 AI 데일리 다이어리 앱입니다.

📂 프로젝트 전체 구조
Aiary/
│
├── backend/                     # FastAPI 서버
│
├── frontend/Android/            # Android(Jetpack Compose) 앱
│
├── models/                      # 학습 코드 + 다운로드 링크 안내
│
└── README.md                    # 현재 문서

✨ 핵심 기능 요약
🧠 AI 기능
기능	사용 기술
한 줄 일기 생성	GPT-4.1-mini Vision API
하루 요약 줄글 생성	GPT-4.1-mini 텍스트 요약
줄글 일기 생성(최종)	KoBART fine-tuned 모델 (팀 모델 담당 제공)
📡 백엔드(FastAPI)

사진 업로드 API

한 줄 일기 생성 API

하루 줄글 일기 생성 API(GPT)

하루 줄글 일기 생성 API(KoBART 모델)

User 회원가입/로그인

PostgreSQL 저장

AWS EC2 배포

📱 프론트(Android)

Jetpack Compose UI

사진 업로드

생성된 일기 보기

Calendar 기반 일기 리스트

마이페이지

Retrofit 통신

🚀 실행 방법
🔹 백엔드
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows는 venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000


문서 보기 →
http://127.0.0.1:8000/docs

🔹 Android 앱 실행
Android Studio → Open → frontend/Android
에뮬레이터 선택 → Run

🔹 모델 배치(Google Drive 다운로드)

Google Drive 모델 다운로드 링크:
👉 https://drive.google.com/drive/folders/1bZPq1JaPhUTS6As8tW0tvMUuIcHYiIXl

다운로드 후 아래 위치에 저장:

backend/models/day_diary_from_summary_v2/

👥 Contributors
역할	담당
백엔드	윤수빈
프론트엔드	팀원
AI 모델	팀 모델 담당
