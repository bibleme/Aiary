package com.example.aiary

import android.content.Context
import android.net.Uri
import android.os.Build
import androidx.annotation.RequiresApi
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit
import java.util.Locale
import com.example.aiary.data.StoryBookData
import com.example.aiary.data.StoryEvent
import com.example.aiary.data.UserSession
import com.example.aiary.network.RetrofitClient
import java.io.File
import java.io.FileOutputStream

private val White = Color(0xFFFFFFFF)

@RequiresApi(Build.VERSION_CODES.O)
@Composable
fun HomeScreen(onNavigateToUpload: () -> Unit,
               onLogout: () -> Unit) {
    val context = LocalContext.current
    // 핸드폰 저장소(SharedPreferences) 불러오기
    val sharedPreferences = remember {
        context.getSharedPreferences("aiary_prefs", Context.MODE_PRIVATE)
    }

    var selectedItem by remember { mutableIntStateOf(0) }
    val items = listOf("홈", "카드형", "리포트", "마이페이지")
    val icons = listOf(Icons.Filled.Home, Icons.Filled.List, Icons.Filled.DateRange, Icons.Filled.Person)

    // 저장소에서 값 불러오기 (없으면 기본값)
    // 이름 불러오기
    var sharedBabyName by remember {
        mutableStateOf(sharedPreferences.getString("baby_name", "시우") ?: "시우")
    }
    // 생일 불러오기
    var sharedBabyBirthDate by remember {
        mutableStateOf(sharedPreferences.getString("baby_birth", "2024-01-01") ?: "2024-01-01")
    }
    // 사진 주소 불러오기
    var sharedProfileUri by remember {
        val uriString = sharedPreferences.getString("baby_photo", null)
        mutableStateOf(if (uriString != null) Uri.parse(uriString) else null)
    }


    // D-Day 계산 로직
    val (currentDateString, dDayString) = remember(sharedBabyBirthDate) {
        val now = LocalDate.now()
        val birthDate = try {
            LocalDate.parse(sharedBabyBirthDate)
        } catch (e: Exception) {
            LocalDate.of(2024, 1, 1)
        }
        val formatter = DateTimeFormatter.ofPattern("yyyy년 M월 d일 EEEE", Locale.KOREAN)
        val formattedDate = now.format(formatter)
        val daysBetween = ChronoUnit.DAYS.between(birthDate, now) + 1
        val dDay = "D+$daysBetween"
        formattedDate to dDay
    }

    Scaffold(
        containerColor = BackgroundBeige,
        bottomBar = {
            NavigationBar(containerColor = White, tonalElevation = 8.dp) {
                items.forEachIndexed { index, item ->
                    NavigationBarItem(
                        icon = { Icon(icons[index], contentDescription = item) },
                        label = { Text(item) },
                        selected = selectedItem == index,
                        onClick = { selectedItem = index },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = PrimaryBlue,
                            selectedTextColor = PrimaryBlue,
                            indicatorColor = BackgroundBeige
                        )
                    )
                }
            }
        }
    ) { innerPadding ->
        Box(modifier = Modifier.padding(innerPadding)) {
            when (selectedItem) {
                0 -> {
                    // 홈 화면
                    Column(
                        modifier = Modifier.fillMaxSize().padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center
                    ) {
                        Text(text = currentDateString, fontSize = 14.sp, color = Color.Gray,
                            modifier = Modifier.padding(bottom = 8.dp))
                        Text(text = "$sharedBabyName 와 만난 지", fontSize = 20.sp, color = DarkGray)
                        Spacer(modifier = Modifier.height(7.dp))
                        Text(text = dDayString, fontSize = 55.sp, fontWeight = FontWeight.Bold, color = PrimaryBlue,
                            modifier = Modifier.padding(bottom = 40.dp))

                        // 중앙 사진
                        Box(
                            contentAlignment = Alignment.Center,
                            modifier = Modifier
                                .size(220.dp)
                                .shadow(10.dp, CircleShape)
                                .clip(CircleShape)
                                .background(White)
                                .border(6.dp, White, CircleShape)
                        ) {
                            if (sharedProfileUri != null) {
                                AsyncImage(
                                    model = sharedProfileUri,
                                    contentDescription = "아이 사진",
                                    contentScale = ContentScale.Crop,
                                    modifier = Modifier.fillMaxSize().padding(6.dp).clip(CircleShape)
                                )
                            } else {
                                Image(
                                    painter = painterResource(id = R.drawable.baby_icon),
                                    contentDescription = "기본 아이콘",
                                    contentScale = ContentScale.Crop,
                                    modifier = Modifier.fillMaxSize().padding(20.dp)
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(24.dp))
                        Text(text = "오늘도 쑥쑥 자라고 있어요 🌱", fontSize = 16.sp, color = DarkGray, fontWeight = FontWeight.Medium)
                        Spacer(modifier = Modifier.height(30.dp))
                        Button(
                            onClick = { onNavigateToUpload() },
                            colors = ButtonDefaults.buttonColors(containerColor = PrimaryBlue),
                            shape = RoundedCornerShape(50.dp),
                            modifier = Modifier.fillMaxWidth(0.8f).height(56.dp)
                        ) {
                            Text("오늘의 기록 남기기 📸", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = White)
                        }
                    }
                }
                1 -> {
                    var diaryState by remember { mutableStateOf("CALENDAR") }
                    var selectedDate by remember { mutableStateOf("") }
                    if (diaryState == "CALENDAR") {
                        CalendarScreen(onDateClick = { date -> selectedDate = date; diaryState = "DIARY" })
                    } else {
                        CardDiaryScreen(selectedDate = selectedDate, onBack = { diaryState = "CALENDAR" })
                    }
                }
                2 -> {
                    var storyData by remember { mutableStateOf<StoryBookData?>(null) }
                    LaunchedEffect(Unit) {
                        try {
                            val myId = UserSession.userId
                            val response = RetrofitClient.api.getDiaries(myId)
                            if (response.isSuccessful) {
                                val diaries = response.body() ?: emptyList()
                                if (diaries.isNotEmpty()) {
                                    val mainPhoto = diaries.last().image_url
                                    val events = diaries.take(3).map { StoryEvent("기록",
                                        listOf(it.image_url), it.content) }
                                    storyData = StoryBookData("2025.12", mainPhoto,
                                        "이번 달에는 총 ${diaries.size}개의 추억이 있습니다.", events)
                                }
                            }
                        } catch (e: Exception) { e.printStackTrace() }
                    }
                    if (storyData != null) BookStoryScreen(storyData = storyData!!, onBack = { selectedItem = 0 })
                    else Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text("리포트 생성 중...", color = Color.Gray) }
                }
                3 -> {
                    MyPageScreen(
                        onLogout = onLogout,
                        currentBabyName = sharedBabyName,
                        currentBabyBirthDate = sharedBabyBirthDate,
                        currentProfileUri = sharedProfileUri,
                        // 정보가 바뀔 때마다 저장소(Preferences)에도 저장
                        onUpdateProfile = { newName, newDate ->
                            sharedBabyName = newName
                            sharedBabyBirthDate = newDate

                            // 영구 저장
                            sharedPreferences.edit()
                                .putString("baby_name", newName)
                                .putString("baby_birth", newDate)
                                .apply()
                        },
                        onUpdateProfileImage = { newUri ->
                            try {
                                val inputStream = context.contentResolver.openInputStream(newUri)
                                val file = File(context.filesDir, "baby_profile.jpg")
                                val outputStream = FileOutputStream(file)

                                inputStream?.copyTo(outputStream)
                                inputStream?.close()
                                outputStream.close()

                                val savedUri = Uri.fromFile(file)

                                sharedProfileUri = savedUri
                                sharedPreferences.edit()
                                    .putString("baby_photo", savedUri.toString())
                                    .apply()

                            } catch (e: Exception) {
                                e.printStackTrace() // 복사 실패 시 로그 출력
                            }
                        }
                    )
                }
            }
        }
    }
}
