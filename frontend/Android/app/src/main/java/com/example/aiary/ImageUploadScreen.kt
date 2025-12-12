package com.example.aiary

import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.aiary.data.UserSession
import com.example.aiary.network.RetrofitClient
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody

@Composable
fun ImageUploadScreen(onBack: () -> Unit) {
    var selectedImageUri by remember { mutableStateOf<android.net.Uri?>(null) }
    var isLoading by remember { mutableStateOf(false) } // 로딩 상태

    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    // 사진 선택기
    val galleryLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia()
    ) { uri ->
        selectedImageUri = uri // 선택한 사진의 주소를 변수에 저장
    }

    // 전체 화면을 Box로 감싸서 로딩 화면을 위에 겹칠 수 있게 함
    Box(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(Color(0xFFFDF5E6))
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // 상단 네비게이션
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 16.dp, bottom = 40.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(onClick = { onBack() }) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = "뒤로 가기",
                        tint = Color.Black
                    )
                }
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "사진 업로드",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.Black
                )
            }

            // 사진 업로드 영역
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(300.dp)
                    .background(Color.White, shape = RoundedCornerShape(16.dp))
                    .clickable {
                        // 박스 클릭 시 갤러리 열기
                        galleryLauncher.launch(
                            PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                        )
                    },
                contentAlignment = Alignment.Center
            ) {
                // 테두리 점선
                val stroke = Stroke(width = 5f, pathEffect = PathEffect.dashPathEffect(floatArrayOf(20f, 20f), 0f))
                Canvas(modifier = Modifier.fillMaxSize()) {
                    drawRoundRect(color = Color(0xFFa7c5eb), style = stroke, cornerRadius = androidx.compose.ui.geometry.CornerRadius(16.dp.toPx()))
                }

                // 내용물: 사진 선택 여부에 따라 다르게 보여줌
                if (selectedImageUri == null) {
                    // 선택 안 됨: + 아이콘
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(text = "+", fontSize = 50.sp, color = Color(0xFFa7c5eb))
                        Text(text = "사진을 선택하거나 드래그하세요", color = Color(0xFF888888), fontSize = 14.sp)
                    }
                } else {
                    // 선택 됨: 체크 아이콘과 파일명 표시 (Coil 라이브러리가 없어서 텍스트로 대체)
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(
                            imageVector = Icons.Filled.CheckCircle,
                            contentDescription = "선택됨",
                            tint = Color(0xFFa7c5eb),
                            modifier = Modifier.size(60.dp)
                        )
                        Spacer(modifier = Modifier.height(10.dp))
                        Text(
                            text = "사진이 선택되었습니다!",
                            color = Color.Black,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Text(
                text = "최대 10장까지 선택 가능합니다.\n아이의 표정이 잘 보이는 사진이 좋아요!",
                color = Color(0xFF888888),
                fontSize = 12.sp,
                textAlign = androidx.compose.ui.text.style.TextAlign.Center
            )

            Spacer(modifier = Modifier.weight(1f))

            // 분석 시작 버튼
            Button(
                onClick = {
                    if (selectedImageUri == null) {
                        Toast.makeText(context, "먼저 사진을 선택해주세요!", Toast.LENGTH_SHORT).show()
                        return@Button
                    }

                    isLoading = true // 로딩 시작

                    coroutineScope.launch {
                        try {
                            // Uri -> 실제 파일로 변환
                            val file = getFileFromUri(context, selectedImageUri!!)

                            if (file != null) {
                                // Multipart 형식으로 변환
                                val requestFile = file.asRequestBody("image/*".toMediaTypeOrNull())
                                val body = MultipartBody.Part.createFormData("photo", file.name, requestFile)
                                val myId = UserSession.userId.toString()
                                val userIdBody = myId.toRequestBody("text/plain".toMediaTypeOrNull())

                                // 서버로 전송 (Retrofit)
                                val response = RetrofitClient.api.createDiary(userIdBody, body)

                                if (response.isSuccessful) {
                                    val result = response.body()
                                    // 성공 시 로직
                                    Toast.makeText(context, "AI 일기 생성 완료!", Toast.LENGTH_LONG).show()
                                    println("생성된 일기: ${result?.diary?.content}")

                                    // TODO: 여기서 결과 화면으로 이동하거나 다이어리 탭으로 이동
                                    onBack() // 임시로 홈으로 이동

                                } else {
                                    Toast.makeText(context, "서버 오류: ${response.code()}", Toast.LENGTH_SHORT).show()
                                }
                            } else {
                                Toast.makeText(context, "파일을 읽을 수 없습니다.", Toast.LENGTH_SHORT).show()
                            }
                        } catch (e: Exception) {
                            Toast.makeText(context, "통신 오류: ${e.message}", Toast.LENGTH_SHORT).show()
                            e.printStackTrace()
                        } finally {
                            isLoading = false
                        }
                    }
                },
                enabled = !isLoading, // 로딩 중엔 버튼 비활성화
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFa7c5eb)),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth().height(56.dp)
            ) {
                if (isLoading) {
                    // 로딩 중이면 버튼 안에 작은 뺑뺑이 표시
                    CircularProgressIndicator(
                        color = Color.White,
                        modifier = Modifier.size(24.dp)
                    )
                } else {
                    Text("AI 분석 시작", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = Color.White)
                }
            }
        }

        // 전체 화면 로딩 오버레이 (선택사항: 화면 전체를 막고 싶을 때)
        if (isLoading) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color.Black.copy(alpha = 0.4f))
                    .clickable(enabled = false) {}, // 터치 막기
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    CircularProgressIndicator(color = Color(0xFFa7c5eb))
                    Spacer(modifier = Modifier.height(16.dp))
                    Text("AI가 열심히 분석 중입니다... 🤖", color = Color.White, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
fun ImageUploadScreenPreview() {
    ImageUploadScreen(onBack = {})
}

// Context를 이용해서 Uri -> 실제 파일로 변환하는 함수 (그대로 유지)
fun getFileFromUri(context: android.content.Context, uri: android.net.Uri): java.io.File? {
    val inputStream = context.contentResolver.openInputStream(uri) ?: return null
    val tempFile = java.io.File.createTempFile("upload", ".jpg", context.cacheDir)
    tempFile.outputStream().use { output ->
        inputStream.copyTo(output)
    }
    return tempFile
} // 251210 수정
