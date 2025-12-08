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
import androidx.compose.ui.platform.LocalContext

// 색상 정의
val PrimaryBlue = Color(0xFFa7c5eb)
val DarkGray = Color(0xFF333333)
val BackgroundBeige = Color(0xFFFDF5E6)

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
    val logoFontFamily = FontFamily(Font(R.font.jalnan)) // 폰트 파일이 있는지 확인 필요
    val coroutineScope = rememberCoroutineScope()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundBeige)
            .padding(horizontal = 32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        // --- 로고 영역 ---
        Image(
            painter = painterResource(id = R.drawable.baby_icon),
            contentDescription = "AIary Logo",
            modifier = Modifier
                .size(100.dp)
                .padding(bottom = 8.dp)
        )

        Text(
            text = "AIary",
            fontSize = 36.sp,
            fontWeight = FontWeight.Black,
            color = DarkGray,
            fontFamily = logoFontFamily
        )
        Text(
            text = "우리아이의 소중한 하루 기록",
            color = Color.Gray,
            fontSize = 14.sp,
            modifier = Modifier.padding(bottom = 48.dp)
        )

        // --- 입력 필드 ---
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

        // --- 로그인 버튼 ---
        Button(
            onClick = {
                // 1. 빈칸 검사
                if (email.isEmpty() || password.isEmpty()) {
                    Toast.makeText(context, "이메일과 비밀번호를 입력해주세요.", Toast.LENGTH_SHORT).show()
                    return@Button
                }

                // 2. 서버 로그인 요청
                coroutineScope.launch {
                    try {
                        val trimmedEmail = email.trim()
                        val trimmedPassword = password.trim()

                        val loginRequest = LoginRequest(email = trimmedEmail, password = trimmedPassword) // 1. 포장하기
                        val response = RetrofitClient.api.login(loginRequest)

                        if (response.isSuccessful) {
                            val body = response.body()
                            val token = body?.accessToken // 서버가 준 토큰 받기

                            // 성공 메시지
                            Toast.makeText(context, "로그인 성공!", Toast.LENGTH_SHORT).show()
                            Log.d("LOGIN", "로그인 성공! User ID: ${body?.user_id}")
                            // Log.d("LOGIN", "Token: $token") // 로그캣에서 확인용

                            // TODO: 받은 token을 SharedPreferences에 저장하는 로직이 여기에 들어가야 합니다.

                            onLoginSuccess() // 홈 화면 이동
                        } else {
                            // 400, 401 에러 등
                            Toast.makeText(context, "로그인 실패: 아이디/비번을 확인하세요.", Toast.LENGTH_SHORT).show()
                            Log.e("LOGIN_FAIL", "Code: ${response.code()}, Error: ${response.errorBody()?.string()}")
                        }
                    } catch (e: Exception) {
                        Toast.makeText(context, "서버 연결 오류: ${e.message}", Toast.LENGTH_SHORT).show()
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

        // --- 하단 버튼들 ---
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
