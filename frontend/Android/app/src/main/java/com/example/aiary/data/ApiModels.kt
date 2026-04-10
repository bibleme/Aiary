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



data class DailyDiaryResponse(
    val id: Int,
    val user_id: Int,
    val diary_date: String,
    val content: String,
    val source_count: Int,
    val created_at: String,
    val updated_at: String
)

// 하루 일기 수정 요청
data class UpdateDiaryContentRequest(
    val content: String
)


// 비밀번호 변경 요청
data class ChangePasswordRequest(
    val old_password: String,
    val new_password: String
)


data class DiaryResponse(
    val id: Int,
    val user_id: Int,
    val content: String,
    val image_url: String,
    val created_at: String,

    @SerializedName("diary_date")
    val diary_date: String? = null
)

data class DeleteAccountResponse(
    val message: String,
    val relogin_required: Boolean,
    val error_code: String
)

data class MonthlyReportResponse(
    val user_id: Int,
    val month: String,
    val mode: String?,
    val month_overview: String,
    val pattern_summary: String,
    val change_summary: String,
    val parent_note: String,
    val one_line_summary: String,
    val keyword_annotations: Map<String, List<KeywordAnnotation>>?,
    val keyword_photo_index: Map<String, KeywordInfo>?,
    val photo_library: List<PhotoInfo>?,
    val generated_at: String?
)

// 상태 확인 API의 응답 데이터 클래스
data class MonthlyReportStatusResponse(
    val user_id: Int,
    val month: String,
    val exists: Boolean,
    val is_up_to_date: Boolean,
    val source_diary_count: Int,
    val stored_source_diary_count: Int?,
    val generated_at: String?,
    val updated_at: String?,
    val reason: String?
)

// 에러 처리용 (일기 5개 미만 등)
data class ErrorResponse(
    val detail: String
)

data class KeywordAnnotation(
    val start: Int,
    val end: Int,
    val keyword: String,
    val keyword_type: String,
    val photo_count: Int,
    val photos: List<PhotoInfo>
)

data class KeywordInfo(
    val keyword: String,
    val keyword_type: String,
    val photo_count: Int,
    val photos: List<PhotoInfo>
)

data class PhotoInfo(
    val diary_id: Int,
    val date: String,
    val image_url: String,
    val full_image_url: String,
    val content: String
)
