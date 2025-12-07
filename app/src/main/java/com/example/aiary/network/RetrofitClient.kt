package com.example.aiary.network

import com.example.aiary.data.*
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.RequestBody
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*


// 2. 통신 기계 (RetrofitClient) - 설정이 완벽하여 그대로 유지합니다.
object RetrofitClient {
    // AWS EC2 주소 (끝에 / 필수)
    private const val BASE_URL = "http://43.200.66.182:8000/"

    // 로그캣에서 통신 내용을 보기 위한 설정
    private val logging = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val client = OkHttpClient.Builder()
        .addInterceptor(logging)
        .build()

    // 외부에서 RetrofitClient.api 로 접근해서 사용
    val api: ApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}