
# 📱 Aiary Android App – Jetpack Compose

사진 업로드 → 한 줄 일기 → 하루 일기 → 달력 기반 관리
전체 흐름을 제공하는 Android 앱입니다.

---

## 📂 폴더 구조

```
frontend/Android/app/src/main/java/com/example/aiary/
│
├── data/
│   ├── ApiModels.kt
│   ├── UserSession.kt
│
├── network/
│   ├── ApiService.kt
│   └── RetrofitClient.kt
│
├── ui/
│   ├── HomeScreen.kt
│   ├── ImageUploadScreen.kt
│   ├── CalendarScreen.kt
│   ├── BookDiaryScreen.kt
│   ├── SignUpScreen.kt
│   └── MypageScreen.kt
```

---

## 🔗 백엔드 서버 연결

`RetrofitClient.kt`:

```kotlin
private const val BASE_URL = "http://<EC2_OR_LOCAL_IP>:8000/"
```

AWS 서버가 켜져 있다면:

```kotlin
http://15.164.215.237:8000/
```

---

## ▶ 앱 실행 방법

1️⃣ Android Studio 실행
2️⃣ `frontend/Android` 폴더 열기
3️⃣ 에뮬레이터 실행
4️⃣ Run 버튼 클릭
5️⃣ 백엔드 서버 실행 필수

---

