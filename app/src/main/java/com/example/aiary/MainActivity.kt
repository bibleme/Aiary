package com.example.aiary

import com.example.aiary.data.LoginRequest
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.aiary.network.RetrofitClient
import com.example.aiary.ui.theme.AiaryLoginTheme
import kotlinx.coroutines.launch
import android.util.Base64
import com.example.aiary.data.UserSession
import org.json.JSONObject
import androidx.compose.ui.layout.ContentScale

// 색상 정의
val PrimaryBlue = Color(0xFF87CEFA)
val DarkGray = Color(0xFF333333)
val BackgroundBeige = Color(0xFFFFF99E)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            AiaryLoginTheme {
                val context = LocalContext.current
                // 화면 상태 관리
                // 0: 로그인, 1: 홈, 2: 업로드, 3: 회원가입
                var currentScreen by remember { mutableIntStateOf(0) }

                Scaffold(
                    modifier = Modifier.fillMaxSize(),
                    containerColor = BackgroundBeige,
                    contentWindowInsets = WindowInsets(0.dp)
                ) { innerPadding ->
                    Box(modifier = Modifier.padding(innerPadding)) {
                        when (currentScreen) {
                            0 -> LoginScreen(
                                onLoginSuccess = { currentScreen = 1 },
                                onSignUpClick = { currentScreen = 3 }
                            )
                            1 -> HomeScreen(onNavigateToUpload = { currentScreen = 2 },
                                onLogout = {
                                    currentScreen = 0
                                    Toast.makeText(context, "로그아웃 되었습니다.", Toast.LENGTH_SHORT).show()
                                }
                            )
                            2 -> ImageUploadScreen(onBack = { currentScreen = 1 })
                            3 -> SignUpScreen(onNavigateToLogin = { currentScreen = 0 })
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun LoginScreen(
    onLoginSuccess: () -> Unit,
    onSignUpClick: () -> Unit
) {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    val context = LocalContext.current
    val logoFontFamily = FontFamily(Font(R.font.jalnan)) 
    val coroutineScope = rememberCoroutineScope()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundBeige)
            .padding(horizontal = 32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        // 로고
        Image(
            painter = painterResource(id = R.drawable.aiary_logo),
            contentDescription = "AIary Logo",
            modifier = Modifier
                .width(200.dp) 
                // .height(100.dp)
                .padding(bottom = 16.dp),
            contentScale = ContentScale.Fit 
        )

        Text(
            text = "우리아이의 소중한 하루 기록",
            color = Color.Gray,
            fontSize = 14.sp,
            modifier = Modifier.padding(bottom = 48.dp)
        )

        // 입력 필드
        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text("이메일 주소") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth(),
            colors = OutlinedTextFieldDefaults.colors(
                focusedContainerColor = Color.White,
                unfocusedContainerColor = Color.White,
                focusedBorderColor = PrimaryBlue,
                unfocusedBorderColor = Color.Gray
            )
        )
        Spacer(modifier = Modifier.height(16.dp))

        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("비밀번호") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            visualTransformation = PasswordVisualTransformation(),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth(),
            colors = OutlinedTextFieldDefaults.colors(
                focusedContainerColor = Color.White,
                unfocusedContainerColor = Color.White,
                focusedBorderColor = PrimaryBlue,
                unfocusedBorderColor = Color.Gray
            )
        )

        Spacer(modifier = Modifier.height(32.dp))

        // 로그인 버튼
        Button(
            onClick = {
                if (email.isEmpty() || password.isEmpty()) {
                    Toast.makeText(context, "이메일과 비밀번호를 입력해주세요.", Toast.LENGTH_SHORT).show()
                    return@Button
                }

                coroutineScope.launch {
                    try {
                        val request = LoginRequest(email, password)
                        val response = RetrofitClient.api.login(request)

                        if (response.isSuccessful) {
                            val body = response.body()
                            val accessToken = body?.access_token

                            if (accessToken != null) {
                                // JWT 토큰에서 user_id 추출하기
                                val userId = getUserIdFromToken(accessToken)
                                UserSession.userId = userId
                                UserSession.userEmail = email  // 입력했던 이메일 저장
                                UserSession.accessToken = accessToken

                                Toast.makeText(context, "로그인 성공! (User ID: $userId)", Toast.LENGTH_SHORT).show()

                                // TODO: 나중엔 accessToken과 userId를 Preference에 저장해야 함

                                onLoginSuccess() // 홈으로 이동
                            } else {
                                Toast.makeText(context, "토큰 응답 오류", Toast.LENGTH_SHORT).show()
                            }
                        } else {
                            Toast.makeText(context, "로그인 실패: 정보를 확인하세요.", Toast.LENGTH_SHORT).show()
                        }
                    } catch (e: Exception) {
                        Toast.makeText(context, "오류: ${e.message}", Toast.LENGTH_SHORT).show()
                        e.printStackTrace()
                    }
                }
            },
            colors = ButtonDefaults.buttonColors(containerColor = PrimaryBlue),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier
                .fillMaxWidth()
                .height(50.dp)
        ) {
            Text("로그인", fontSize = 18.sp, fontWeight = FontWeight.SemiBold, color = Color.White)
        }

        Spacer(modifier = Modifier.height(16.dp))

        // 하단 버튼들
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            TextButton(onClick = { /* TODO: 비밀번호 찾기 */ }) {
                Text(
                    text = "비밀번호 찾기",
                    color = Color.Gray,
                    textDecoration = TextDecoration.Underline,
                    fontSize = 13.sp
                )
            }
            TextButton(onClick = { onSignUpClick() }) {
                Text(
                    text = "회원가입",
                    color = PrimaryBlue,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 13.sp
                )
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
fun LoginScreenPreview() {
    AiaryLoginTheme {
        LoginScreen(onLoginSuccess = {}, onSignUpClick = {})
    }
}

// JWT 토큰 디코딩 함수
fun getUserIdFromToken(token: String): Int {
    try {
        // JWT는 3부분(Header.Body.Signature)으로 나뉨. Body(1번 인덱스)만 필요함.
        val parts = token.split(".")
        if (parts.size < 2) return -1

        val payload = String(Base64.decode(parts[1], Base64.URL_SAFE))
        val json = JSONObject(payload)

        // 백엔드 user.py에서 'sub'에 user.id를 넣었음
        return json.getString("sub").toInt()
    } catch (e: Exception) {
        e.printStackTrace()
        return -1
    }
}

