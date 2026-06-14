
# 📱 Aiary Android App – Jetpack Compose

사진 업로드 → 한 줄 일기 → 하루 일기 → 월간 리포트
전체 흐름을 제공하는 Android 앱입니다.

---

## 📂 폴더 구조

```
frontend/Android/app/src/main/java/com/example/aiary/
│
├── data/
│   ├── ApiModels.kt
│   ├── StoryBookData.kt
│   └── UserSession.kt
│
├── network/
│   ├── ApiService.kt
│   └── RetrofitClient.kt
│
├── ui/theme/
│   ├── Color.kt
│   ├── Theme.kt
│   ├── Type.kt

├── BookStoryScreen.kt
├── HomeScreen.kt
├── ImageUploadScreen.kt
├── CalendarScreen.kt
├── LoginViewModel
├── ReportWrapperScreen.kt
├── MainActivity.kt
├── CardDiary.kt
├── SignUpScreen.kt
├── MypageScreen.kt
└── MypageViewModel
```

---

## 🔗 백엔드 서버 연결

`RetrofitClient.kt`:

```kotlin
private const val BASE_URL = "[http://3.35.185.251:8000/](http://3.35.185.251:8000/)"
```

---

## ▶ 앱 실행 방법

1️⃣ Android Studio 실행
2️⃣ `frontend/Android` 폴더 열기
3️⃣ 안드로이드 스마트폰 기기 연결 또는 에뮬레이터 실행
4️⃣ Run 버튼 클릭

---

