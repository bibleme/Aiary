package com.example.aiary.network

import com.example.aiary.data.*
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.PUT // PUT 메서드 사용
import retrofit2.http.Part

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

    // 일기 생성 (이미지 업로드)
    @Multipart
    @POST("diaries/")
    suspend fun createDiary(
        @Part("baby_id") babyId: RequestBody,
        @Part photo: MultipartBody.Part
    ): Response<DiaryResponse>

    // 비밀번호 변경 (여기 추가된 것입니다!)
    @PUT("users/password")
    suspend fun changePassword(
        @Body request: ChangePasswordRequest
    ): Response<Unit>
}
