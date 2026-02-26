package com.example.aiary

import android.app.DatePickerDialog
import android.widget.DatePicker
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
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
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.aiary.data.UserSession
import com.example.aiary.network.RetrofitClient
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.Calendar // 👇 날짜 선택을 위해 추가

val UploadPrimaryBlue = Color(0xFF87CEFA)
val UploadBackgroundBeige = Color(0xFFFFF99E)
val UploadDarkGray = Color(0xFF333333)

@Composable
fun ImageUploadScreen(onBack: () -> Unit) {
    var selectedImageUri by remember { mutableStateOf<android.net.Uri?>(null) }
    var isLoading by remember { mutableStateOf(false) }

    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    // 👇 [추가 1] 날짜 선택을 위한 상태 변수와 달력(Calendar) 설정
    val calendar = Calendar.getInstance()
    var selectedDate by remember {
        // 기본값: 오늘 날짜 (예: 2025-12-14)
        val year = calendar.get(Calendar.YEAR)
        val month = String.format("%02d", calendar.get(Calendar.MONTH) + 1)
        val day = String.format("%02d", calendar.get(Calendar.DAY_OF_MONTH))
        mutableStateOf("$year-$month-$day")
    }

    // 👇 [추가 2] 안드로이드 기본 달력 팝업 (DatePickerDialog) 설정
    val datePickerDialog = DatePickerDialog(
        context,
        { _: DatePicker, year: Int, month: Int, dayOfMonth: Int ->
            val formattedMonth = String.format("%02d", month + 1)
            val formattedDay = String.format("%02d", dayOfMonth)
            selectedDate = "$year-$formattedMonth-$formattedDay" // 선택한 날짜로 업데이트
        },
        calendar.get(Calendar.YEAR),
        calendar.get(Calendar.MONTH),
        calendar.get(Calendar.DAY_OF_MONTH)
    )

    val galleryLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == android.app.Activity.RESULT_OK) {
            // 사진을 선택하고 돌아왔을 때 URI를 가져옴
            selectedImageUri = result.data?.data
        }
    }

    Box(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(UploadBackgroundBeige)
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // 상단 네비게이션
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 16.dp, bottom = 24.dp), // 간격 살짝 조절
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(onClick = { onBack() }) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = "뒤로 가기",
                        tint = UploadDarkGray
                    )
                }
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "사진 업로드",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = UploadDarkGray
                )
            }

            // 👇 [추가 3] 날짜 선택 입력칸 (클릭하면 달력 팝업 뜸)
            OutlinedTextField(
                value = selectedDate,
                onValueChange = {},
                label = { Text("기록할 날짜") },
                readOnly = true, // 타이핑 금지, 클릭만 가능하게
                trailingIcon = {
                    IconButton(onClick = { datePickerDialog.show() }) {
                        Icon(painterResource(android.R.drawable.ic_menu_my_calendar), contentDescription = "달력 아이콘")
                    }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { datePickerDialog.show() }
                    .padding(bottom = 24.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = UploadPrimaryBlue,
                    unfocusedBorderColor = Color.Gray
                )
            )

            // 사진 업로드 영역
            Box(
                 modifier = Modifier
                    .fillMaxWidth()
                    .height(300.dp)
                    .background(Color.White, shape = RoundedCornerShape(16.dp))
                    .clickable {
                        // 👇 [수정] "모든 이미지(EXTERNAL_CONTENT_URI)"를 가져오는 갤러리 실행 인텐트!
                        val intent = android.content.Intent(
                            android.content.Intent.ACTION_PICK,
                            android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI
                        )
                        galleryLauncher.launch(intent)
                    },
                contentAlignment = Alignment.Center
            ) {
                val stroke = Stroke(width = 5f, pathEffect = PathEffect.dashPathEffect(floatArrayOf(20f, 20f), 0f))
                Canvas(modifier = Modifier.fillMaxSize()) {
                    drawRoundRect(
                        color = UploadPrimaryBlue,
                        style = stroke,
                        cornerRadius = androidx.compose.ui.geometry.CornerRadius(16.dp.toPx())
                    )
                }

                if (selectedImageUri == null) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(text = "+", fontSize = 50.sp, color = UploadPrimaryBlue)
                        Text(text = "사진을 선택하거나 드래그하세요", color = Color.Gray, fontSize = 14.sp)
                    }
                } else {
                    Box(modifier = Modifier.fillMaxSize()) {
                        AsyncImage(
                            model = selectedImageUri,
                            contentDescription = "선택된 사진",
                            contentScale = ContentScale.Crop,
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(2.dp)
                        )
                        Icon(
                            imageVector = Icons.Filled.CheckCircle,
                            contentDescription = null,
                            tint = UploadPrimaryBlue,
                            modifier = Modifier
                                .align(Alignment.TopEnd)
                                .padding(10.dp)
                                .size(30.dp)
                                .background(Color.White, CircleShape)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Text(
                text = "최대 10장까지 선택 가능합니다.\n아이의 표정이 잘 보이는 사진이 좋아요!",
                color = Color.Gray,
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
                    isLoading = true
                    coroutineScope.launch {
                        try {
                            val file = getFileFromUri(context, selectedImageUri!!)
                            if (file != null) {
                                val requestFile = file.asRequestBody("image/*".toMediaTypeOrNull())
                                val body = MultipartBody.Part.createFormData("photo", file.name, requestFile)

                                val myId = UserSession.userId.toString()
                                val userIdBody = myId.toRequestBody("text/plain".toMediaTypeOrNull())

                                // 👇 [추가 4] 선택한 날짜도 서버에 같이 보내기 위해 변환
                                val dateBody = selectedDate.toRequestBody("text/plain".toMediaTypeOrNull())

                                // 🚨 [주의] 백엔드와 연결된 Retrofit API 코드 수정 필요 (아래 설명 참고)
                                val response = RetrofitClient.api.createDiary(userIdBody, dateBody, body)

                                if (response.isSuccessful) {
                                    Toast.makeText(context, "AI 일기 생성 완료!", Toast.LENGTH_LONG).show()
                                    file.delete()
                                    onBack()
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
                enabled = !isLoading,
                colors = ButtonDefaults.buttonColors(
                    containerColor = UploadPrimaryBlue,
                    disabledContainerColor = Color.LightGray
                ),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth().height(56.dp)
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        color = Color.White,
                        modifier = Modifier.size(24.dp)
                    )
                } else {
                    Text("AI 분석 시작", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = Color.White)
                }
            }
        }

        if (isLoading) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color.Black.copy(alpha = 0.4f))
                    .clickable(enabled = false) {},
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    CircularProgressIndicator(color = UploadPrimaryBlue)
                    Spacer(modifier = Modifier.height(16.dp))
                    Text("AI가 열심히 분석 중입니다... 🤖", color = Color.White, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

// ... preview와 getFileFromUri 함수는 기존과 동일
@Preview(showBackground = true)
@Composable
fun ImageUploadScreenPreview() {
    ImageUploadScreen(onBack = {})
}

fun getFileFromUri(context: android.content.Context, uri: android.net.Uri): java.io.File? {
    val inputStream = context.contentResolver.openInputStream(uri) ?: return null
    val tempFile = java.io.File.createTempFile("upload", ".jpg", context.cacheDir)
    tempFile.outputStream().use { output ->
        inputStream.copyTo(output)
    }
    return tempFile
}
