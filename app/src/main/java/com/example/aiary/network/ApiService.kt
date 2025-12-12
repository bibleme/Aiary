package com.example.aiary.network

import com.example.aiary.data.*
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import com.example.aiary.data.ChangePasswordRequest
import retrofit2.http.*

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

    // 사진 업로드 및 한 줄 일기 생성
    @Multipart
    @POST("diaries/")
    suspend fun createDiary(
        // 🚨 백엔드는 'user_id'를 원함 (기존 baby_id에서 수정됨!)
        @Part("user_id") userId: RequestBody,
        @Part photo: MultipartBody.Part
    ): Response<CreateDiaryResponse>

    // 하루 줄글 일기 생성 (KoBART)
    @POST("diaries/summary-json")
    suspend fun createFullDiary(
        @Body request: DaySummaryRequest
    ): Response<FullDiaryResponse>

    @POST("/users/change-password")
    suspend fun changePassword(
        @Body request: ChangePasswordRequest
    ): Response<Any>

    // 유저별 일기 리스트 조회
    @GET("diaries/")
    suspend fun getDiaries(
        @Query("user_id") userId: Int
    ): Response<List<DiaryResponse>>
}
