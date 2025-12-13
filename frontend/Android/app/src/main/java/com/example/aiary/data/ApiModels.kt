package com.example.aiary.data

import javax.annotation.processing.Generated
import com.google.gson.annotations.SerializedName

// 1. 로그인 요청
data class LoginRequest(
    val email: String,
    val password: String
)

// 2. 로그인 응답 (백엔드 user.py 참고: Token 모델)
// user_id가 없고 access_token만 옴 -> 나중에 토큰에서 id 추출해야 함
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

// 5. 일기 생성 응답 (백엔드 diary.py: create_diary 반환값 참고)
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

// 하루 줄글 일기(Full Diary) 요청
data class DaySummaryRequest(
    val user_id: Int,
    val date: String // "YYYY-MM-DD"
)


data class FullDiaryResponse(
    val status: String,
    val full_diary: String?, // KoBART가 만든 줄글 일기
    val bullet_lines: List<String>?,
    val combined_summary: String?
 )


// 비밀번호 변경 요청
data class ChangePasswordRequest(
    val email: String,
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
