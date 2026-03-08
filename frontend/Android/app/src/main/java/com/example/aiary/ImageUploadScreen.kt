package com.example.aiary

import android.app.DatePickerDialog
import android.widget.DatePicker
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.result.PickVisualMediaRequest // 👇 필수 추가
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow // 👇 필수 추가
import androidx.compose.foundation.lazy.items // 👇 필수 추가
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
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
import java.util.Calendar

val UploadPrimaryBlue = Color(0xFF87CEFA)
val UploadBackgroundBeige = Color(0xFFFFF99E)
val UploadDarkGray = Color(0xFF333333)

@Composable
fun ImageUploadScreen(onBack: () -> Unit) {
    var selectedImageUris by remember { mutableStateOf<List<android.net.Uri>>(emptyList()) }
    var isLoading by remember { mutableStateOf(false) }

    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    val calendar = Calendar.getInstance()
    var selectedDate by remember {
        val year = calendar.get(Calendar.YEAR)
        val month = String.format("%02d", calendar.get(Calendar.MONTH) + 1)
        val day = String.format("%02d", calendar.get(Calendar.DAY_OF_MONTH))
        mutableStateOf("$year-$month-$day")
    }

    val datePickerDialog = DatePickerDialog(
        context,
        { _: DatePicker, year: Int, month: Int, dayOfMonth: Int ->
            val formattedMonth = String.format("%02d", month + 1)
            val formattedDay = String.format("%02d", dayOfMonth)
            selectedDate = "$year-$formattedMonth-$formattedDay"
        },
        calendar.get(Calendar.YEAR),
        calendar.get(Calendar.MONTH),
        calendar.get(Calendar.DAY_OF_MONTH)
    )

    // 10장 다중 선택 전용 런처
    val galleryLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickMultipleVisualMedia(maxItems = 10)
    ) { uriList ->
        if (uriList.isNotEmpty()) {
            selectedImageUris = uriList
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
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 16.dp, bottom = 24.dp),
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

            OutlinedTextField(
                value = selectedDate,
                onValueChange = {},
                label = { Text("기록할 날짜") },
                readOnly = true,
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

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(300.dp)
                    .background(Color.White, shape = RoundedCornerShape(16.dp))
                    .clickable {
                        // 다중 선택 갤러리를 띄우는 올바른 인텐트 방식
                        galleryLauncher.launch(
                            PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                        )
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

                //  null 체크가 아니라 isEmpty()로 체크하고, LazyRow로 여러 장 띄우기!
                if (selectedImageUris.isEmpty()) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(text = "+", fontSize = 50.sp, color = UploadPrimaryBlue)
                        Text(text = "사진을 최대 10장까지 선택하세요", color = Color.Gray, fontSize = 14.sp)
                    }
                } else {
                    LazyRow(
                        modifier = Modifier.fillMaxSize().padding(8.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        items(selectedImageUris) { uri ->
                            Box(modifier = Modifier.fillMaxHeight().aspectRatio(1f)) {
                                AsyncImage(
                                    model = uri,
                                    contentDescription = "선택된 사진",
                                    contentScale = ContentScale.Crop,
                                    modifier = Modifier
                                        .fillMaxSize()
                                        .clip(RoundedCornerShape(8.dp))
                                )
                                Icon(
                                    imageVector = Icons.Filled.CheckCircle,
                                    contentDescription = null,
                                    tint = UploadPrimaryBlue,
                                    modifier = Modifier
                                        .align(Alignment.TopEnd)
                                        .padding(8.dp)
                                        .size(24.dp)
                                        .background(Color.White, CircleShape)
                                )
                            }
                        }
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

            Button(
                onClick = {
                    if (selectedImageUris.isEmpty()) { 
                        Toast.makeText(context, "먼저 사진을 선택해주세요!", Toast.LENGTH_SHORT).show()
                        return@Button
                    }
                    isLoading = true
                    coroutineScope.launch {
                        try {
                            val myId = UserSession.userId.toString()
                            val userIdBody = myId.toRequestBody("text/plain".toMediaTypeOrNull())
                            val dateBody = selectedDate.toRequestBody("text/plain".toMediaTypeOrNull())

                            val sharedPref = context.getSharedPreferences("aiary_prefs", android.content.Context.MODE_PRIVATE)
                            val savedToken = UserSession.accessToken
                            val bearerToken = "Bearer $savedToken"

                            var successCount = 0

                            // 실패했을 때 서버가 보낸 에러 내용을 담아둘 변수
                            var lastErrorCode = 0
                            var lastErrorMsg = ""

                            for (uri in selectedImageUris) {
                                val file = getFileFromUri(context, uri)
                                if (file != null) {
                                    val requestFile = file.asRequestBody("image/*".toMediaTypeOrNull())
                                    val body = MultipartBody.Part.createFormData("photo", file.name, requestFile)

                                    val response = RetrofitClient.api.createDiary(bearerToken, userIdBody, dateBody, body)

                                    if (response.isSuccessful) {
                                        successCount++
                                    } else {
                            
                                        lastErrorCode = response.code()
                                        lastErrorMsg = response.errorBody()?.string() ?: "알 수 없는 에러"
                                    }
                                    file.delete()
                                }
                            }

                            if (successCount > 0) {
                                Toast.makeText(context, "${successCount}장의 AI 일기 생성 완료!", Toast.LENGTH_LONG).show()
                                onBack()
                            } else {
                                // 진짜 에러 원인을 토스트 메시지로 띄웁니다
                                Toast.makeText(context, "에러($lastErrorCode): $lastErrorMsg", Toast.LENGTH_LONG).show()
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
                    Text("AI 분석 시작 (${selectedImageUris.size}장)", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = Color.White)
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
