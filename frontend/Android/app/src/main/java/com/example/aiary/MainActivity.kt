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

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.aiary.ui.theme.AiaryLoginTheme
import kotlinx.coroutines.launch

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

                // 앱이 켜질 때 딱 한 번 실행되는 검사기 (LaunchedEffect)
                LaunchedEffect(Unit) {
                    val sharedPref = context.getSharedPreferences("aiary_prefs",
                        android.content.Context.MODE_PRIVATE)
                    val savedToken = sharedPref.getString("accessToken", null)
                    val savedUserId = sharedPref.getInt("userId", -1)
                    val savedEmail = sharedPref.getString("userEmail", "")

                    // 저장된 토큰이 있다면? -> UserSession을 복구하고 바로 홈 화면으로
                    if (savedToken != null && savedUserId != -1) {
                        UserSession.accessToken = savedToken
                        UserSession.userId = savedUserId
                        UserSession.userEmail = savedEmail ?: ""
                        currentScreen = 1 // 0(로그인)을 건너뛰고 바로 1(홈)로 이동
                    }
                }


                Scaffold(
                    modifier = Modifier.fillMaxSize(),
                    containerColor = BackgroundBeige,
                    contentWindowInsets = WindowInsets(0.dp)
                ) { innerPadding ->
                    Box(modifier = Modifier.padding(innerPadding)) {
                        AnimatedContent(
                            targetState = currentScreen,
                            transitionSpec = {
                                // 화면이 오른쪽에서 밀려 들어오고 왼쪽으로 살짝 빠지는 슬라이드 효과
                                (slideInHorizontally(
                                    animationSpec = tween(400),
                                    initialOffsetX = { fullWidth -> fullWidth }
                                ) + fadeIn(animationSpec = tween(400))) togetherWith
                                        (slideOutHorizontally(
                                            animationSpec = tween(400),
                                            targetOffsetX = { fullWidth -> -fullWidth / 3 }
                                        ) + fadeOut(animationSpec = tween(400)))
                            },
                            label = "Screen Transition"
                        ) { targetScreen ->
                            // 반드시 currentScreen 대신 'targetScreen'을 써야 애니메이션이 안 꼬입니다
                            when (targetScreen) {
                                0 -> LoginScreen(
                                    onLoginSuccess = { currentScreen = 1 },
                                    onSignUpClick = { currentScreen = 3 }
                                )
                                1 -> HomeScreen(
                                    onNavigateToUpload = { currentScreen = 2 },
                                    onLogout = {
                                        UserSession.clear()
                                        val sharedPref = context.getSharedPreferences("aiary_prefs",
                                            android.content.Context.MODE_PRIVATE)
                                        sharedPref.edit()
                                            .remove("accessToken")
                                            .remove("userId")
                                            .remove("userEmail")
                                            .apply()

                                        currentScreen = 0
                                        Toast.makeText(context, "로그아웃 되었습니다.",
                                            Toast.LENGTH_SHORT).show()
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
        // 로고
        Image(
            painter = painterResource(id = R.drawable.aiary_logo),
            contentDescription = "AIary Logo",
            modifier = Modifier
                .width(200.dp) // 로고의 가로 너비
                // .height(100.dp) // 필요하면 높이도 지정 가능
                .padding(bottom = 16.dp),
            contentScale = ContentScale.Fit // 이미지 비율 유지하며 맞춤
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

                                // 핸드폰 창고(SharedPreferences)에 정보 저장하기
                                val sharedPref = context.getSharedPreferences("aiary_prefs", android.content.Context.MODE_PRIVATE)
                                with(sharedPref.edit()) {
                                    putString("accessToken", accessToken)
                                    putInt("userId", userId)
                                    putString("userEmail", email)
                                    apply() // 이걸 꼭 해야 저장이 완료됩니다.
                                }

                                Toast.makeText(context, "로그인 성공! (User ID: $userId)", Toast.LENGTH_SHORT).show()

                                onLoginSuccess() // 홈으로 이동
                            } else {
                                Toast.makeText(context, "토큰 응답 오류", Toast.LENGTH_SHORT).show()
                            }
                        } else {
                            Toast.makeText(context, "로그인 실패: 정보를 확인하세요.",
                                Toast.LENGTH_SHORT).show()
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

// JWT 토큰 디코딩 함수
fun getUserIdFromToken(token: String): Int {
    try {
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

