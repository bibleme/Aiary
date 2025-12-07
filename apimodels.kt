package com.example.aiary.data

// 로그인 요청 보낼 때 쓸 데이터
data class LoginRequest(
    val email: String,
    val password: String
)

// 로그인 성공 시 서버가 주는 응답 (백엔드 코드 참고: message, user_id)
data class LoginResponse(
    val message: String,
    val user_id: Int
)

// 일기 생성 성공 시 서버가 주는 응답
data class DiaryResponse(
    val status: String,
    val diary_text: String,
    val image_url: String? // URL은 없을 수도 있으니 nullable
)

// 회원가입 요청 데이터
data class RegisterRequest(
    val email: String,
    val password: String
)

// 회원가입 응답 데이터
data class UserResponse(
    val id: Int,
    val email: String,
    val created_at: String
)