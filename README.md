# Aiary (AI 기반 육아 일기 생성 프로젝트)

## 1. 프로젝트 개요

Aiary는 아이의 하루를 기록하기 위해  
- **사진 업로드**
- **한 줄 일기 작성**
- **하루 줄글 일기 자동 생성**

기능을 제공하는 AI 기반 육아 일기 서비스입니다.

구성 요소는 세 부분으로 나뉩니다.

- **backend/** : FastAPI 기반 백엔드 서버  
- **frontend/Android/** : Jetpack Compose 기반 안드로이드 앱  
- **models/** : 한 줄 일기 / 하루 줄글 일기 생성에 사용한 모델 및 노트북

---

## 2. 디렉터리 구조

```text
backend/           FastAPI 서버 (API, DB, 설정 등)
frontend/Android/  Android 앱 프로젝트 (Jetpack Compose UI)
models/            모델 관련 데이터 및 Jupyter 노트북
