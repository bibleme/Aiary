# 🌿 **Aiary – AI 기반 사진 자동 일기 생성 서비스**

Aiary는 **아기의 사진을 올리면 자동으로 한 줄 일기와 하루 줄글 일기**를 생성해주는 AI 서비스입니다.

* 📸 **사진 → 한 줄 일기 (GPT Vision 기반)**
* ✏️ **여러 한 줄 일기 → 하루 요약 줄글 일기(GPT 텍스트 요약)**
* 📘 **최종 하루 줄글 일기 → KoBART fine-tuned 모델 생성**

FastAPI 백엔드 + Android 프론트 + KoBART 모델이 하나의 프로젝트에서 통합된 AI 데일리 다이어리 앱입니다.

---

## 📂 **프로젝트 전체 구조**

```
Aiary/
│
├── backend/                 # FastAPI 서버
│
├── frontend/Android/        # Android Jetpack Compose 앱
│
├── models/                  # 학습 코드 + KoBART 모델 다운로드 안내
│
└── README.md                # 루트 README
```

---

## ✨ **핵심 기능 요약**

### 🧠 **AI 기능**

| 기능             | 사용 기술                            |
| -------------- | -------------------------------- |
| 한 줄 일기 생성      | GPT-4.1-mini Vision API          |
| 하루 요약 줄글 생성    | GPT-4.1-mini 텍스트 요약              |
| 하루 줄글 일기 최종 생성 | KoBART fine-tuned 모델(팀 모델 담당 제공) |

---

### 🖥 **백엔드(FastAPI)**

* 사진 업로드 API
* 한 줄 일기 생성 API
* 하루 줄글 일기 생성 API (GPT)
* 하루 줄글 일기 생성 API (KoBART fine-tuned 모델)
* User 회원가입/로그인
* PostgreSQL 저장
* AWS EC2 배포

---

### 📱 **프론트엔드(Android)**

* Jetpack Compose UI
* 사진 업로드 화면
* 생성된 일기 리스트
* Calendar 기반 일기 기록
* 마이페이지
* Retrofit 기반 서버 통신

---

## 📦 **모델 다운로드 안내**

학습된 KoBART 모델은 용량 때문에 GitHub에 포함되지 않음.
아래 드라이브에서 다운로드:

👉 [https://drive.google.com/drive/folders/1bZPq1JaPhUTS6As8tW0tvMUuIcHYiIXl](https://drive.google.com/drive/folders/1bZPq1JaPhUTS6As8tW0tvMUuIcHYiIXl)

다운로드 후 복사 경로:

```
backend/models/day_diary_from_summary_v2/
```

---

## 🚀 **백엔드 실행 방법**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Swagger → [(http://3.35.185.251:8000/docs)]

---

## ▶️ **프론트 실행 방법**

```
Android Studio → Open → frontend/Android
에뮬레이터 실행 → Run
```

---

## 👥 **Contributors**

| 역할       | 담당      |
| -------- | ------- |
| 백엔드      | 윤수빈 , 임규민 |
| 프론트엔드    | 도한비 |
| AI Model | 류혁, 정성경 |

---


