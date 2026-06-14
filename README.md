![Aiary Logo](https://github.com/bibleme/Aiary/raw/main/logo.png)

# 🌿 **Aiary – AI 기반 사진 자동 일기 생성 서비스**

Aiary는 **아기의 사진을 올리면 자동으로 한 줄 일기와 하루 줄글 일기**를 생성해주는 AI 서비스입니다.

* 📸 **사진 → 한 줄 일기 (GPT Vision 기반)**
* ✏️ **여러 한 줄 일기 → 하루 요약 줄글 일기(GPT 텍스트 요약)**
* 📘 **최종 하루 줄글 일기 → KoBART fine-tuned 모델 생성**

FastAPI 백엔드 + Android 프론트 + PostgreSQL 데이터베이스 + AWS S3 이미지 저장소 + NLP 및 CV 분석 모듈이 하나의 프로젝트에서 통합된 AI 데일리 다이어리 앱입니다.

---

## ✔️ **프로젝트 배경**
* 사진은 많지만 기록할 시간 부족
* 기존 육아일기 앱의 높은 수동 입력
* 일반 AI 캡션의 맥락 부족

-> Aiary는 사진 중심·자동·개인화 일기를 통해 부모의 기록 부담을 줄이고, 아이의 성장을 더 의미 있게 남깁니다. 


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
| 하루 줄글 일기 생성 | KoBART fine-tuned 모델 |
| 월간 리포트 생성 | GPT + CV |

---

### 🖥 **CV** 
wiki page: https://github.com/bibleme/Aiary/wiki/CV

* 한 줄 일기 생성 (GPT)
* 하루 일기 생성 (KoBART)
* CV 기반 구조화 데이터 생성 (CV 배치 워커 실행)
* 한 줄 일기·하루 일기·CV 분석 결과를 활용한 월별 스토리 리포트 생성(GPT)
* 월간 리포트 UI 및 통계 시각화에 분석 결과 반영

---

### 📱 **NLP**
wiki page: https://github.com/bibleme/Aiary/wiki/NLP

* 한 줄 일기 생성 (GPT-4.1-mini)
* 하루 일기 생성 (fine-tuned KoBART)
* 학습 데이터 구성 (Round 1~Round 5)
* 월간 리포트 (GPT)

---

### 🖥 **백엔드(FastAPI)**
wiki page: https://github.com/bibleme/Aiary/wiki/Backend
* 사진 업로드 API
* 한 줄 일기 생성 API
* 하루 줄글 일기 생성 API (GPT)
* 하루 줄글 일기 생성 API (KoBART fine-tuned 모델)
* User 회원가입/로그인
* PostgreSQL 저장
* AWS EC2 배포

---

### 📱 **프론트엔드(Android)**
wiki page: https://github.com/bibleme/Aiary/wiki

* Jetpack Compose UI
* 사진 업로드 화면
* 생성된 일기 리스트
* Calendar 기반 일기 기록
* 월간 리포트
* 마이페이지
* Retrofit 기반 서버 통신

---

## 📦 **모델 다운로드 안내**

학습된 KoBART 모델은 용량 때문에 GitHub에 포함되지 않음.
아래 링크에서 다운로드:

👉 [https://huggingface.co/bibleme/daily_aiary_v6/tree/main/kobart_student_round5_realistic_daily]

---

## 🚀 **백엔드 실행 방법**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Swagger → [http://3.35.185.251:8000/docs](http://3.35.185.251:8000/docs)

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


