package com.example.aiary.data

import com.google.gson.annotations.SerializedName

// 1. 회원가입 요청
data class RegisterRequest(
    val email: String,
    val password: String
)

// 2. 회원가입 응답
// (서버가 주는 필드만 받아야 에러가 안 납니다. 모르는 건 null 처리)
data class UserResponse(
    val id: Int,
    val email: String,
    // created_at이나 is_active는 서버가 안 주면 에러나니까 nullable(?) 처리
    val is_active: Boolean? = null,
    val created_at: String? = null
)

// 🚨 3. 로그인 요청 (이게 새로 추가된 핵심입니다!)
// 서버가 JSON으로 받기 때문에 이 객체가 꼭 필요합니다.
data class LoginRequest(
    @SerializedName("email")
    val email: String,

    @SerializedName("password")
    val password: String
)

// 🚨 4. 로그인 응답 (서버 코드에 맞춰 수정함)
// 아까 백엔드 코드가 return {"message": "...", "user_id": ...} 였으므로
// 여기에 맞춰야 앱이 안 튕깁니다.
data class LoginResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String,
    // [선택 사항] 서버에서 user_id를 같이 안 주므로, 이 필드는 제거하거나 null 처리합니다.
    val user_id: Int? = null
)

// 5. 일기 생성 응답
data class DiaryResponse(
    val status: String,
    val diary_text: String,
    val image_url: String?
)

// 비밀번호 변경 요청 데이터
data class ChangePasswordRequest(
    val email: String, // 누군지 알아야 하니 이메일 추가
    val current_password: String,
    val new_password: String
)
