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
import androidx.compose.runtime.*
import kotlinx.coroutines.launch

@Composable
fun ReportWrapperScreen(
    targetMonth: String, // 예: "2026-03"
    onBack: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    var isLoading by remember { mutableStateOf(true) }
    var reportStatus by remember { mutableStateOf<MonthlyReportStatusResponse?>(null) }

    // 1️⃣ 두 종류의 데이터를 담을 상태(State) 변수
    var reportData by remember { mutableStateOf<MonthlyReportResponse?>(null) }
    var cvData by remember { mutableStateOf<CVMonthlySummaryResponse?>(null) }

    var errorMessage by remember { mutableStateOf<String?>(null) }

    // 초기 상태 조회 및 데이터 로딩
    LaunchedEffect(targetMonth) {
        val token = "Bearer ${UserSession.accessToken}"
        try {
            val statusRes = RetrofitClient.api.getMonthlyReportStatus(targetMonth, token)
            if (statusRes.isSuccessful && statusRes.body() != null) {
                val status = statusRes.body()!!
                reportStatus = status

                if (status.exists) {
                    val reportRes = RetrofitClient.api.getMonthlyReport(targetMonth, token)
                    // CV는 항상 최신 조회
                    val cvRes = RetrofitClient.api.getCvMonthlySummary(targetMonth, token)

                    if (reportRes.isSuccessful && cvRes.isSuccessful) {
                        reportData = reportRes.body()
                        cvData = cvRes.body()
                    }
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
            errorMessage = "데이터를 불러오는 중 오류가 발생했습니다."
        } finally {
            isLoading = false
        }
    }

    // 리포트 생성/업데이트 요청 함수
    val handleGenerateRequest = { isRegenerate: Boolean ->
        coroutineScope.launch {
            isLoading = true
            errorMessage = null
            val token = "Bearer ${UserSession.accessToken}"
            try {
                // 2️⃣ 리포트 생성(혹은 업데이트) 요청
                val response = if (isRegenerate) {
                    RetrofitClient.api.regenerateMonthlyReport(targetMonth, token)
                } else {
                    RetrofitClient.api.generateMonthlyReport(targetMonth, token)
                }

                if (response.isSuccessful) {
                    // 생성 성공 시 글 데이터를 먼저 받고,
                    // 이어서 사진(CV) 데이터도 즉시 불러옵니다.
                    reportData = response.body()
                    val cvRes = RetrofitClient.api.getCvMonthlySummary(targetMonth, token)
                    if (cvRes.isSuccessful) {
                        cvData = cvRes.body()
                    }
                } else {
                    val errorBody = response.errorBody()?.string()
                    if (errorBody != null) {
                        val json = JSONObject(errorBody)
                        errorMessage = json.optString("detail", "리포트 생성 요건을 확인해 주세요.")
                    }
                }
            } catch (e: Exception) {
                errorMessage = "네트워크 연결 상태를 확인해 주세요."
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
    }
    // 3️⃣ 글 데이터와 사진 데이터가 모두 있어야 책 화면으로 진입합니다.
    else if (reportData != null && cvData != null) {
        BookStoryScreen(
            reportData = reportData!!,
            cvData = cvData!!,
            isUpToDate = reportStatus!!.is_up_to_date, 
            onRegenerate = { handleGenerateRequest(true) }, 
            onBack = onBack
        )
    }
    else if (reportStatus != null) {
        Column(
            modifier = Modifier.fillMaxSize().padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text("📚 $targetMonth 리포트", fontSize = 24.sp, color = DarkGray, modifier = Modifier.padding(bottom = 16.dp))

            if (!reportStatus!!.exists) {
                Text("아직 이 달의 리포트가 없어요.\n지금 바로 만들어 볼까요?", color = Color.Gray, modifier = Modifier.padding(bottom = 32.dp))
                Button(onClick = { handleGenerateRequest(false) }) {
                    Text("리포트 생성하기 ✨")
                }
            } else if (!reportStatus!!.is_up_to_date) {
                Text("새로운 일기가 추가되었네요!\n리포트를 최신 내용으로 업데이트 할까요?", color = Color.Gray, modifier = Modifier.padding(bottom = 32.dp))
                Button(onClick = { handleGenerateRequest(true) }) {
                    Text("리포트 업데이트 🔄")
                }
            }

            else {
                Text("리포트 데이터를 완전히 불러오지 못했어요.\n리포트를 다시 생성해 보시겠어요?", color = Color.Gray, modifier = Modifier.padding(bottom = 32.dp))
                Button(onClick = { handleGenerateRequest(true) }) {
                    Text("리포트 복구(재생성) 🛠️")
                }
            }

            if (errorMessage != null) {
                Spacer(modifier = Modifier.height(16.dp))
                Text(text = errorMessage!!, color = Color.Red, fontSize = 14.sp)
            }

            Spacer(modifier = Modifier.height(20.dp))
            TextButton(onClick = onBack) { Text("뒤로 가기", color = Color.Gray) }
        }
    }
}
