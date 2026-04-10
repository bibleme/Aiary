package com.example.aiary

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import com.example.aiary.data.*
import com.example.aiary.network.RetrofitClient
import org.json.JSONObject

@Composable
fun ReportWrapperScreen(
    targetMonth: String, // 예: "2026-03"
    onBack: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    var isLoading by remember { mutableStateOf(true) }
    var reportStatus by remember { mutableStateOf<MonthlyReportStatusResponse?>(null) }
    var reportData by remember { mutableStateOf<MonthlyReportResponse?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    // 1. 화면이 켜지자마자 가장 먼저 [상태 조회] API를 호출합니다.
    LaunchedEffect(targetMonth) {
        val token = "Bearer ${UserSession.accessToken}"
        try {
            val statusRes = RetrofitClient.api.getMonthlyReportStatus(targetMonth, token)
            if (statusRes.isSuccessful && statusRes.body() != null) {
                val status = statusRes.body()!!
                reportStatus = status

                // 상태 검사: 이미 만들어져 있고, 최신 상태라면 바로 리포트 내용을 조회!
                if (status.exists && status.is_up_to_date) {
                    val reportRes = RetrofitClient.api.getMonthlyReport(targetMonth, token)
                    if (reportRes.isSuccessful) {
                        reportData = reportRes.body()
                    }
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        } finally {
            isLoading = false
        }
    }

    // API 요청 함수 (생성 or 재생성)
    val handleGenerateRequest = { isRegenerate: Boolean ->
        coroutineScope.launch {
            isLoading = true
            errorMessage = null
            val token = "Bearer ${UserSession.accessToken}"
            try {
                val response = if (isRegenerate) {
                    RetrofitClient.api.regenerateMonthlyReport(targetMonth, token)
                } else {
                    RetrofitClient.api.generateMonthlyReport(targetMonth, token)
                }

                if (response.isSuccessful) {
                    reportData = response.body() // 성공하면 바로 책 데이터를 받아서 보여줌
                } else {
                    // 에러 발생 시 (일기 5개 미만 등) 백엔드가 준 detail 메시지를 파싱해서 보여줌
                    val errorBody = response.errorBody()?.string()
                    if (errorBody != null) {
                        val json = JSONObject(errorBody)
                        errorMessage = json.optString("detail", "리포트 생성 중 오류가 발생했습니다.")
                    }
                }
            } catch (e: Exception) {
                errorMessage = "네트워크 오류가 발생했습니다."
            } finally {
                isLoading = false
            }
        }
    }

    // ---------------- UI 렌더링 ----------------
    if (isLoading) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator(color = PrimaryBlue)
        }
    } else if (reportData != null) {
        // [케이스 3] 리포트가 완성된 상태 -> 기존에 만든 예쁜 책 화면 보여주기!
        BookStoryScreen(reportData = reportData!!, onBack = onBack)
    } else if (reportStatus != null) {
        // [케이스 1 & 2] 리포트가 없거나 업데이트가 필요한 상태
        Column(
            modifier = Modifier.fillMaxSize().padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text("📚 $targetMonth 리포트", fontSize = 24.sp, color = DarkGray, modifier = Modifier.padding(bottom = 16.dp))

            if (!reportStatus!!.exists) {
                // exists = false -> 생성 버튼
                Text("아직 이 달의 리포트가 없어요.\n지금 바로 만들어 볼까요?", color = Color.Gray, modifier = Modifier.padding(bottom = 32.dp))
                Button(onClick = { handleGenerateRequest(false) }) {
                    Text("리포트 생성하기 ✨")
                }
            } else if (!reportStatus!!.is_up_to_date) {
                // exists = true & is_up_to_date = false -> 업데이트 버튼
                Text("새로운 일기가 추가되었네요!\n리포트를 최신 내용으로 업데이트 할까요?", color = Color.Gray, modifier = Modifier.padding(bottom = 32.dp))
                Button(onClick = { handleGenerateRequest(true) }) {
                    Text("리포트 업데이트 🔄")
                }
            }

            // 에러 메시지 텍스트 (예: "최소 5개의 기록이 필요해요")
            if (errorMessage != null) {
                Spacer(modifier = Modifier.height(16.dp))
                Text(text = errorMessage!!, color = Color.Red, fontSize = 14.sp)
            }

            Spacer(modifier = Modifier.height(20.dp))
            TextButton(onClick = onBack) { Text("뒤로 가기", color = Color.Gray) }
        }
    }
}
