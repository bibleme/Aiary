package com.example.aiary

import android.content.Context
import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
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
import com.example.aiary.data.UserSession
import com.example.aiary.network.RetrofitClient
import java.io.File
import java.io.FileOutputStream
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.clickable
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed

private val White = Color(0xFFFFFFFF)

@Composable
fun HomeScreen(onNavigateToUpload: () -> Unit,
               onLogout: () -> Unit) {
    val context = LocalContext.current
    val sharedPreferences = remember {
        context.getSharedPreferences("aiary_prefs", Context.MODE_PRIVATE)
    }

    val myId = UserSession.userId
    val handleLogout = {
        onLogout()
    }

    var selectedItem by remember { mutableIntStateOf(0) }
    val items = listOf("홈", "카드형", "리포트", "마이페이지")
    val icons = listOf(Icons.Filled.Home, Icons.Filled.List, Icons.Filled.DateRange, Icons.Filled.Person)

    var sharedBabyName by remember {
        mutableStateOf(sharedPreferences.getString("baby_name_$myId", "@@") ?: "@@")
    }
    var sharedBabyBirthDate by remember {
        mutableStateOf(sharedPreferences.getString("baby_birth_$myId", "2024-01-01") ?: "2024-01-01")
    }
    var sharedProfileUri by remember {
        val uriString = sharedPreferences.getString("baby_photo_$myId", null)
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
                        Text(text = dDayString, fontSize = 55.sp, fontWeight = FontWeight.Bold,
                            color = PrimaryBlue,
                            modifier = Modifier.padding(bottom = 40.dp))

                        // 중앙 사진
                        Box(
                            contentAlignment = Alignment.Center,
                            modifier = Modifier
                                .size(220.dp)
                                .shadow(10.dp, CircleShape)
                                .clip(CircleShape)

                        ) {
                            if (sharedProfileUri != null) {
                                AsyncImage(
                                    model = sharedProfileUri,
                                    contentDescription = "아이 사진",
                                    contentScale = ContentScale.Crop,
                                    modifier = Modifier.fillMaxSize().
                                    //padding(6.dp).
                                    clip(CircleShape)
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
                    // 타입이 단순한 String(월 이름) 리스트로 바뀝니다!
                    var activeMonths by remember { mutableStateOf<List<String>>(emptyList()) }
                    var selectedMonthStr by remember { mutableStateOf<String?>(null) }

                    LaunchedEffect(Unit) {
                        try {
                            val myId = UserSession.userId
                            val token = "Bearer ${UserSession.accessToken}"
                            // 전체 일기 조회해서 일기가 있는 "YYYY-MM"만 쏙쏙 뽑아오기
                            val response = RetrofitClient.api.getDiaries(myId, token)
                            if (response.isSuccessful) {
                                val diaries = response.body() ?: emptyList()
                                activeMonths = diaries.mapNotNull { diary ->
                                    val targetDate = diary.diary_date ?: diary.created_at
                                    if (targetDate.length >= 7) targetDate.substring(0, 7) else null
                                }.distinct().sortedDescending() // 중복 제거 후 최신순 정렬
                            }
                        } catch (e: Exception) { e.printStackTrace() }
                    }

                    if (selectedMonthStr == null) {
                        ReportListScreen(
                            months = activeMonths, // String 리스트 넘김
                            onMonthClick = { monthStr -> selectedMonthStr = monthStr }
                        )
                    } else {
                        ReportWrapperScreen(
                            targetMonth = selectedMonthStr!!,
                            onBack = { selectedMonthStr = null }
                        )
                    }
                }
                3 -> {
                    MyPageScreen(
                        onLogout = handleLogout,
                        onDeleteAccount = onLogout,
                        currentBabyName = sharedBabyName,
                        currentBabyBirthDate = sharedBabyBirthDate,
                        currentProfileUri = sharedProfileUri,
                        onUpdateProfile = { newName, newDate ->
                            sharedBabyName = newName
                            sharedBabyBirthDate = newDate
                            sharedPreferences.edit()
                                .putString("baby_name_$myId", newName)
                                .putString("baby_birth_$myId", newDate)
                                .apply()
                        },
                        onUpdateProfileImage = { newUri ->
                            try {
                                val inputStream = context.contentResolver.openInputStream(newUri)
                                val file = File(context.filesDir, "baby_profile_$myId.jpg")
                                val outputStream = FileOutputStream(file)

                                inputStream?.copyTo(outputStream)
                                inputStream?.close()
                                outputStream.close()

                                val savedUri = Uri.fromFile(file)
                                sharedProfileUri = savedUri

                                sharedPreferences.edit()
                                    .putString("baby_photo_$myId", savedUri.toString())
                                    .apply()

                            } catch (e: Exception) {
                                e.printStackTrace()
                            }
                        }
                    )
                }
            }
        }
    }
}

@Composable
fun ReportListScreen(
    months: List<String>,
    onMonthClick: (String) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundBeige)
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "우리아이 추억 쌓기 📚",
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            color = DarkGray,
            modifier = Modifier
                .align(Alignment.Start)
                .padding(bottom = 32.dp)
        )

        if (months.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("아직 쌓인 추억이 없어요.", color = Color.Gray)
            }
        } else {
            LazyColumn(
                modifier = Modifier.weight(1f).fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(6.dp, Alignment.Bottom)
            ) {
                itemsIndexed(months) { index, monthStr ->
                    StackedBookItem(
                        monthStr = monthStr,
                        index = index,
                        onClick = { onMonthClick(monthStr) }
                    )
                }
            }
        }
    }
}

@Composable
fun StackedBookItem(
    monthStr: String,
    index: Int,
    onClick: () -> Unit
) {
    // 책등 색상 팔레트
    val bookColors = listOf(
        Color(0xFFF2B8B5),
        Color(0xFFE6C2A5),
        Color(0xFFA8C8A6),
        Color(0xFFB5C0D0),
        Color(0xFFD3B8D8)
    )
    val backgroundColor = bookColors[index % bookColors.size]

    // 가로 길이 (삐뚤빼뚤하게)
    val widthFraction = if (index % 2 == 0) 0.85f else 0.95f

    // 책 두께(높이)를 다양하게
    val bookHeights = listOf(45.dp, 65.dp, 50.dp, 75.dp, 55.dp)
    val currentThickness = bookHeights[index % bookHeights.size]

    Card(
        shape = RoundedCornerShape(6.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
        colors = CardDefaults.cardColors(containerColor = backgroundColor),
        modifier = Modifier
            .fillMaxWidth(widthFraction)
            .height(currentThickness)
            .clickable { onClick() }
    ) {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            val displayMonth = monthStr.replace("-", ".")

            Text(
                text = "${displayMonth}의 기록",
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                color = DarkGray
            )
        }
    }
}
