package com.example.aiary.network

import com.example.aiary.data.*
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.*
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Header

interface ApiService {

    // 회원가입
    @POST("users/register")
    suspend fun register(
        @Body request: RegisterRequest
    ): Response<UserResponse>

    // 로그인
    @POST("users/login")
    suspend fun login(
        @Body request: LoginRequest
    ): Response<LoginResponse>

    // 비밀번호 변경 (PUT 방식으로 하나만 남김)
    @PUT("users/password")
    suspend fun changePassword(
        @Header("Authorization") token: String,
        @Body request: ChangePasswordRequest
    ): Response<Unit>

    // 일기 생성
    @Multipart
    @POST("diaries/")
    suspend fun createDiary(
        @Header("Authorization") token: String,
        @Part("user_id") userId: RequestBody,
        @Part("date_str") date: RequestBody,
        @Part photo: MultipartBody.Part
    ): Response<CreateDiaryResponse>

    // 특정 날짜의 하루 일기 조회
    @GET("daily-diaries/{date_str}")
    suspend fun getDailyDiary(
        @Path("date_str") dateStr: String,
        @Query("user_id") userId: Int,
        @Header("Authorization") token: String
    ): Response<DailyDiaryResponse>

    // 하루 일기 최초 1회 생성
    @POST("daily-diaries/")
    suspend fun createDailyDiary(
        @Header("Authorization") token: String,
        @Body request: DaySummaryRequest
    ): Response<DailyDiaryResponse>

    // 유저별 일기 리스트 조회
    @GET("diaries/")
    suspend fun getDiaries(
        @Query("user_id") userId: Int,
        @Header("Authorization") token: String
    ): Response<List<DiaryResponse>>

    // 하루 일기 수정 API
    @PATCH("daily-diaries/{date_str}")
    suspend fun updateDailyDiary(
        @Path("date_str") dateStr: String,
        @Header("Authorization") token: String,
        @Body request: UpdateDiaryContentRequest
    ): Response<DailyDiaryResponse>


    // 일기 삭제
    @DELETE("diaries/{diary_id}")
    suspend fun deleteDiary(
        @Path("diary_id") diaryId: Int,
        @Query("user_id") userId: Int,
        @Header("Authorization") token: String,
    ): Response<Unit>

    // 계정 삭제
    @DELETE("users/me")
    suspend fun deleteAccount(
        @Header("Authorization") token: String
    ): Response<DeleteAccountResponse>

    @GET("monthly-report/status")
    suspend fun getMonthlyReportStatus(
        @Query("target_month") targetMonth: String,
        @Header("Authorization") token: String
    ): Response<MonthlyReportStatusResponse>

    // 월간 리포트 조회
    @GET("monthly-report")
    suspend fun getMonthlyReport(
        @Query("target_month") targetMonth: String,
        @Header("Authorization") token: String
    ): Response<MonthlyReportResponse>

    // 월간 리포트 생성
    @POST("monthly-report/generate")
    suspend fun generateMonthlyReport(
        @Query("target_month") targetMonth: String,
        @Header("Authorization") token: String
    ): Response<MonthlyReportResponse>

    // 월간 리포트 재생성
    @POST("monthly-report/regenerate")
    suspend fun regenerateMonthlyReport(
        @Query("target_month") targetMonth: String,
        @Header("Authorization") token: String
    ): Response<MonthlyReportResponse>


    @GET("/cv/monthly") 
    suspend fun getCvMonthlySummary(
        @Query("target_month") targetMonth: String,
        @Header("Authorization") token: String  
    ): Response<CVMonthlySummaryResponse>


    @PUT("/daily-diaries/{date_str}/regenerate")
    suspend fun regenerateDailyDiary(
        @Path("date_str") dateStr: String, 
        @Header("Authorization") token: String
    ): Response<DailyDiaryResponse>

}

