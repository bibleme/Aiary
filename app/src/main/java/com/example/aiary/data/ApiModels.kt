package com.example.aiary.data

// 1. 로그인 요청
data class LoginRequest(
    val email: String,
    val password: String
)

// 2. 로그인 응답 
data class LoginResponse(
    val access_token: String,
    val token_type: String
)

// 3. 회원가입 요청
data class RegisterRequest(
    val email: String,
    val password: String
)

// 4. 회원가입 응답
data class UserResponse(
    val id: Int,
    val email: String,
    val created_at: String
)

// 5. 일기 생성 응답
// { "status": "success", "diary": { ... } } 형태임
data class CreateDiaryResponse(
    val status: String,
    val diary: DiaryData
)

// 일기 상세 데이터
data class DiaryData(
    val id: Int,
    val user_id: Int,
    val content: String,
    val image_url: String,
    val created_at: String
)

// 6. 하루 줄글 일기(Full Diary) 요청
data class DaySummaryRequest(
    val user_id: Int,
    val date: String // "YYYY-MM-DD"
)

// 7. 하루 줄글 일기 응답
data class FullDiaryResponse(
    val status: String,
    // 서버 -> "generated_diary", 앱 변수명(summary)과 연결
    @SerializedName("generated_diary")
    val summary: String?,
    val bullet_lines: List<String>?,
    val combined_summary: String?
)

// 6. 비밀번호 변경 요청
data class ChangePasswordRequest(
    val email: String,      // 누구인지 식별용
    val current_password: String,
    val new_password: String
)


data class DiaryResponse(
    val id: Int,
    val user_id: Int,
    val content: String,
    val image_url: String,
    val created_at: String
)
