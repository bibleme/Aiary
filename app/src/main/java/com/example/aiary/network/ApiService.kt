package com.example.aiary.network

import com.example.aiary.data.*
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import okhttp3.MultipartBody
import okhttp3.RequestBody

interface ApiService {

    // 1. 회원가입 (변경 없음 - 잘하셨습니다!)
    @POST("users/register")
    suspend fun register(
        @Body request: RegisterRequest
    ): Response<UserResponse>

    // 2. 로그인 (🚨 여기가 중요합니다!)
    // [삭제] @FormUrlEncoded  <-- 이거 꼭 지우세요!
    @POST("users/login")
    suspend fun login(
        // [수정] @Field 대신 @Body를 써야 JSON으로 날아갑니다.
        @Body request: LoginRequest
    ): Response<LoginResponse>

    // 3. 일기 생성 (변경 없음)
    @Multipart
    @POST("diaries/")
    suspend fun createDiary(
        @Part("baby_id") babyId: RequestBody,
        @Part photo: MultipartBody.Part
    ): Response<DiaryResponse>
}