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
import retrofit2.http.DELETE
import retrofit2.http.Path

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

    @PUT("users/password")
    suspend fun changePassword(
        @Header("Authorization") token: String,
        @Body request: ChangePasswordRequest
    ): Response<Unit>
    
    @Multipart
    @POST("diaries/") // 백엔드 주소
    suspend fun createDiary(
        @Part("user_id") userId: RequestBody,
        @Part("date") date: RequestBody,
        @Part photo: MultipartBody.Part
    ): Response<CreateDiaryResponse>

    // 하루 줄글 일기 생성
    @POST("diaries/full")
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

    @DELETE("diaries/{diary_id}")
    suspend fun deleteDiary(
        @Path("diary_id") diaryId: Int,
        @Query("user_id") userId: Int
    ): Response<Unit>
}
