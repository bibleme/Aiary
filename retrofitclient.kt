package com.example.aiary.network

import com.example.aiary.data.DiaryResponse
import com.example.aiary.data.LoginRequest
import com.example.aiary.data.LoginResponse
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.RequestBody
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import com.example.aiary.data.*
import retrofit2.http.Body
import retrofit2.http.POST

// API 명세서 (백엔드 엔드포인트와 일치시켜야 함)
interface ApiService {
    // 로그인
    @POST("users/login")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>

    // 회원가입
    @POST("users/register")
    suspend fun register(@Body request: RegisterRequest): Response<UserResponse>

    // 일기 생성 (이미지 업로드)
    @Multipart
    @POST("diaries/")
    suspend fun createDiary(
        @Part("baby_id") babyId: RequestBody, // 백엔드가 baby_id를 받음
        @Part photo: MultipartBody.Part       // 이미지 파일
    ): Response<DiaryResponse>
}

// 통신 기계 (싱글톤 객체)
object RetrofitClient {
    private const val BASE_URL = "http://43.200.66.182:8000/"

    private val logging = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val client = OkHttpClient.Builder()
        .addInterceptor(logging)
        .build()

    val api: ApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}