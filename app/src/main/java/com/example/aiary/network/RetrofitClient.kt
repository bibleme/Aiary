package com.example.aiary.network

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit 

// 통신 기계 (RetrofitClient)
object RetrofitClient {
    private const val BASE_URL = "http://3.35.185.251:8000/"

    // 로그캣에서 통신 내용을 보기 위한 설정
    private val logging = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    // 타임아웃 설정을 추가한 클라이언트
    private val client = OkHttpClient.Builder()
        .addInterceptor(logging)
        // 서버와 연결되는 시간 제한 (기본 10초 -> 60초로 연장)
        .connectTimeout(60, TimeUnit.SECONDS)
        // 서버가 응답(일기 생성)을 줄 때까지 기다리는 시간 (KoBART가 오래 걸리므로 필수)
        .readTimeout(60, TimeUnit.SECONDS)
        // 데이터를 서버로 보내는 시간 제한 (이미지 업로드 등)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build()

    // 외부에서 RetrofitClient.api 로 접근해서 사용
    val api: ApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(client) // 위에서 만든(시간 늘린) client를 장착
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}
