package com.example.aiary

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
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit
import java.util.Locale
// import com.example.aiary_login.R

// 색상 정의
private val White = Color(0xFFFFFFFF)

@RequiresApi(Build.VERSION_CODES.O)
@Composable
fun HomeScreen(onNavigateToUpload: () -> Unit,
               onLogout: () -> Unit) {
    // 하단바 선택 상태 관리 (0: 홈, 1: 카드형, 2: 스토리, 3: 마이페이지)
    var selectedItem by remember { mutableIntStateOf(0) }

    val items = listOf("홈", "카드형", "스토리", "마이페이지")
    val icons = listOf(
        Icons.Filled.Home,
        Icons.Filled.List,
        Icons.Filled.DateRange,
        Icons.Filled.Person
    )

    // 날짜 및 D-Day 자동 계산 로직
    val (currentDateString, dDayString) = remember {
        val now = LocalDate.now() // 오늘 날짜

        // 아이 생일 설정 (나중엔 서버 데이터로 변경)
        val babyBirthDate = LocalDate.of(2024, 1, 1)

        // 날짜 포맷팅
        val formatter = DateTimeFormatter.ofPattern("yyyy년 M월 d일 EEEE", Locale.KOREAN)
        val formattedDate = now.format(formatter)

        // D-Day 계산
        val daysBetween = ChronoUnit.DAYS.between(babyBirthDate, now) + 1
        val dDay = "D+$daysBetween"

        formattedDate to dDay
    }

    Scaffold(
        containerColor = BackgroundBeige,
        // 하단바
        bottomBar = {
            NavigationBar(
                containerColor = White,
                tonalElevation = 8.dp
            ) {
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
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center
                    ) {
                        // 상단 D-Day 및 날짜
                        Text(
                            text = currentDateString,
                            fontSize = 14.sp,
                            color = Color.Gray,
                            modifier = Modifier.padding(bottom = 8.dp)
                        )
                        Text(
                            text = "@@와 만난 지",
                            fontSize = 20.sp,
                            color = DarkGray
                        )

                        Spacer(modifier = Modifier.height(7.dp))

                        Text(
                            text = dDayString,
                            fontSize = 55.sp,
                            fontWeight = FontWeight.Bold,
                            color = PrimaryBlue,
                            modifier = Modifier.padding(bottom = 40.dp)
                        )

                        // 중앙 아이 대표 사진
                        Box(
                            contentAlignment = Alignment.Center,
                            modifier = Modifier
                                .size(220.dp)
                                .shadow(10.dp, CircleShape)
                                .clip(CircleShape)
                                .background(White)
                                .border(6.dp, White, CircleShape)
                        ) {
                            Image(
                                painter = painterResource(id = R.drawable.baby_icon),
                                contentDescription = "아이 대표 사진",
                                contentScale = ContentScale.Crop,
                                modifier = Modifier.fillMaxSize().padding(20.dp)
                            )
                        }

                        Spacer(modifier = Modifier.height(24.dp))

                        Text(
                            text = "오늘도 쑥쑥 자라고 있어요 🌱",
                            fontSize = 16.sp,
                            color = DarkGray,
                            fontWeight = FontWeight.Medium
                        )

                        Spacer(modifier = Modifier.height(30.dp))

                        // 기록하기 버튼
                        Button(
                            onClick = { onNavigateToUpload() },
                            colors = ButtonDefaults.buttonColors(containerColor = PrimaryBlue),
                            shape = RoundedCornerShape(50.dp),
                            modifier = Modifier
                                .fillMaxWidth(0.8f)
                                .height(56.dp)
                        ) {
                            Text(
                                text = "오늘의 기록 남기기 📸",
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold,
                                color = White
                            )
                        }
                    }
                }

                1 -> {
                    //캘린더 <-> 다이어리 관리
                    var diaryState by remember { mutableStateOf("CALENDAR") }
                    // 선택된 날짜 저장
                    var selectedDate by remember { mutableStateOf("") }

                    if (diaryState == "CALENDAR") {
                        CalendarScreen(
                            onDateClick = { date ->
                                selectedDate = date // 클릭한 날짜 저장
                                diaryState = "DIARY" // 다이어리 화면으로 전환
                            }
                        )
                    } else {
                        CardDiaryScreen(
                            selectedDate = selectedDate, // 저장된 날짜 전달
                            onBack = {
                                diaryState = "CALENDAR" // 다시 캘린더로 복귀
                            }
                        )
                    }
                }

                2 -> {
                    // 스토리 화면
                    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text("스토리 화면 준비 중...", color = Color.Gray)
                    }
                }

                3 -> {
                    // 마이페이지
                    MyPageScreen ( onLogout = onLogout )
                    }
                }
            }
        }
    }


@Preview(showBackground = true)
@Composable
fun HomeScreenPreview() {
    HomeScreen(
        onNavigateToUpload = {},
        onLogout = {}
    )
}
