package com.example.aiary_login

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.aiary_login.ui.theme.AiaryLoginTheme
import androidx.compose.foundation.Image
import androidx.compose.ui.res.painterResource
import android.widget.Toast
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily

val PrimaryBlue = Color(0xFFa7c5eb)
val DarkGray = Color(0xFF333333)
val BackgroundBeige = Color(0xFFFDF5E6)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            AiaryLoginTheme {
                // 화면 상태 관리
                // 0: 로그인 화면, 1: 홈 화면, 2: 사진 업로드 화면
                var currentScreen by remember { mutableIntStateOf(0) }

                Scaffold(
                    modifier = Modifier.fillMaxSize(),
                    containerColor = Color(0xFFFDF5E6),
                    contentWindowInsets = WindowInsets(0.dp)
                ) { innerPadding ->
                    Box(modifier = Modifier.padding(innerPadding)) {
                        when (currentScreen) {
                            0 -> LoginScreen(onLoginSuccess = { currentScreen = 1 }) // 로그인 성공 시 홈으로
                            1 -> HomeScreen(onNavigateToUpload = { currentScreen = 2 }) // 버튼 클릭 시 업로드로
                            2 -> ImageUploadScreen(
                                onBack = {
                                    currentScreen = 1
                                }
                            ) // 업로드 화면
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun LoginScreen(onLoginSuccess: () -> Unit) {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    val context = LocalContext.current
    val logoFontFamily = FontFamily(Font(R.font.jalnan))

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundBeige)
            .padding(horizontal = 32.dp), // 좌우 여백
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        // 로고 및 제목

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

        // 입력 필드

        // 이메일 입력
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
                disabledContainerColor = Color.White,
                focusedBorderColor = PrimaryBlue,
                unfocusedBorderColor = Color.Gray
            )
        )
        Spacer(modifier = Modifier.height(16.dp))

        // 비밀번호 입력
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
                disabledContainerColor = Color.White,
                focusedBorderColor = PrimaryBlue,
                unfocusedBorderColor = Color.Gray
            )
        )

        Spacer(modifier = Modifier.height(32.dp))

        // 로그인 버튼

        Button(
            onClick = {
                // 유효성 검사 로직
                if (email.isEmpty() || password.isEmpty()) {
                    Toast.makeText(context, "이메일과 비밀번호를 입력해주세요.", Toast.LENGTH_SHORT).show()
                }
                else if (!email.contains("@")) {
                    Toast.makeText(context, "올바른 이메일 형식이 아닙니다.", Toast.LENGTH_SHORT).show()
                }
                else if (password.length < 6) {
                    Toast.makeText(context, "비밀번호는 6자리 이상이어야 합니다.", Toast.LENGTH_SHORT).show()
                }
                else {
                    // 모든 조건 통과 시 화면 전환 신호 보내기
                    Toast.makeText(context, "로그인 성공!", Toast.LENGTH_SHORT).show()

                    // MainActivity에서 넘겨준 함수 실행 -> currentScreen이 1로 바뀜
                    onLoginSuccess()
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

        // 비번 찾기 및 회원가입

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            TextButton(onClick = { /* TODO: 비밀번호 찾기 화면 이동 */ }) {
                Text(
                    text = "비밀번호 찾기",
                    color = Color.Gray,
                    textDecoration = TextDecoration.Underline,
                    fontSize = 13.sp
                )
            }
            TextButton(onClick = { /* TODO: 회원가입 화면 이동 */ }) {
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

// LoginScreen 미리보기
@Preview(showBackground = true)
@Composable
fun LoginScreenPreview() {
    AiaryLoginTheme {
        // onLoginSuccess = {}
        LoginScreen(onLoginSuccess = {})
    }
}