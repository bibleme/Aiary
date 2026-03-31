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
import com.example.aiary.data.StoryBookData
import com.example.aiary.data.StoryEvent
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
                    var reportList by remember { mutableStateOf<List<StoryBookData>>(emptyList()) }
                    var selectedReport by remember { mutableStateOf<StoryBookData?>(null) }

                    // 각 월(Month)별 전체 사진들을 저장해둘 공간 (표지 변경 기능에 쓰임)
                    var monthPhotosMap by remember { mutableStateOf<Map<String, List<String>>>(emptyMap()) }

                    LaunchedEffect(Unit) {
                        try {
                            val myId = UserSession.userId
                            val bearerToken = "Bearer ${UserSession.accessToken}"
                            val response = RetrofitClient.api.getDiaries(myId, bearerToken)
                            if (response.isSuccessful) {
                                val diaries = response.body() ?: emptyList()

                                if (diaries.isNotEmpty()) {
                                    // 서버에서 온 일기들을 "YYYY.MM" (예: 2025.12) 단위로 그룹화(묶기) 합니다.
                                    val groupedDiaries = diaries.groupBy { diary ->
                                        // date 대신 데이터 클래스에 있는 diary_date를 사용
                                        // 만약 diary_date가 비어있을(null) 경우를 대비해 created_at을 예비용으로 쓰도록 안전장치(?:)도 걸어두었습니다.
                                        val targetDate = diary.diary_date ?: diary.created_at

                                        if (targetDate.length >= 7) {
                                            targetDate.substring(0, 7).replace("-", ".")
                                        } else {
                                            "알 수 없음"
                                        }
                                    }

                                    val tempReportList = mutableListOf<StoryBookData>()
                                    val tempPhotosMap = mutableMapOf<String, List<String>>()

                                    // 2. 묶여진 월별 일기들을 바탕으로 진짜 책(리포트)을 만듭니다.
                                    for ((monthStr, monthDiaries) in groupedDiaries) {
                                        // 해당 월의 모든 사진 주소 정리
                                        val photoUrls = monthDiaries.map { diary ->
                                            if (diary.image_url.startsWith("http")) diary.image_url
                                            else "http://3.35.185.251:8000${diary.image_url}"
                                        }
                                        tempPhotosMap[monthStr] = photoUrls

                                        // 해당 월의 이벤트 추출
                                        val events = monthDiaries.take(3).map { diary ->
                                            val fixedEventUrl = if (diary.image_url.startsWith("http"))
                                                diary.image_url else "http://3.35.185.251:8000${diary.image_url}"
                                            StoryEvent("기록", listOf(fixedEventUrl), diary.content)
                                        }

                                        // 리포트 1권 완성
                                        tempReportList.add(
                                            StoryBookData(
                                                month = monthStr, // "2025.12" 등
                                                mainPhotoUrl = photoUrls.last(), // 가장 최근 사진을 표지로
                                                summary = "${monthStr}의 소중한 추억들입니다. " +
                                                        "(총 ${monthDiaries.size}개의 기록)", // 임시 요약글
                                                events = events
                                            )
                                        )
                                    }

                                    // 최신 달이 맨 앞에 오도록 정렬해서 저장
                                    reportList = tempReportList.sortedByDescending { it.month }
                                    monthPhotosMap = tempPhotosMap
                                }
                            }
                        } catch (e: Exception) { e.printStackTrace() }
                    }

                    if (selectedReport == null) {
                        ReportListScreen(
                            reports = reportList,
                            onReportClick = { report -> selectedReport = report }
                        )
                    } else {
                        BookStoryScreen(
                            storyData = selectedReport!!,
                            // 내가 선택한 달(month)의 사진들만 팝업에 넘겨줌!
                            allMonthPhotoUrls = monthPhotosMap[selectedReport!!.month] ?: emptyList(),
                            onBack = { selectedReport = null }
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
    reports: List<StoryBookData>,
    onReportClick: (StoryBookData) -> Unit
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

        if (reports.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("아직 쌓인 추억이 없어요.", color = Color.Gray)
            }
        } else {
            LazyColumn(
                modifier = Modifier.weight(1f).fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(6.dp, Alignment.Bottom)
            ) {
                itemsIndexed(reports) { index, report ->
                    StackedBookItem(report = report, index = index, onClick = { onReportClick(report) })
                }
            }
        }
    }
}

@Composable
fun StackedBookItem(
    report: StoryBookData,
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

    // 책 두께(높이)를 다양하게 리스트로 만듭니다!
    val bookHeights = listOf(45.dp, 65.dp, 50.dp, 75.dp, 55.dp)
    // 인덱스에 맞춰서 두께를 하나씩 꺼내옵니다.
    val currentThickness = bookHeights[index % bookHeights.size]

    Card(
        shape = RoundedCornerShape(6.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
        colors = CardDefaults.cardColors(containerColor = backgroundColor),
        modifier = Modifier
            .fillMaxWidth(widthFraction)
            // 고정값 대신 위에서 만든 변수를 넣어줍니다
            .height(currentThickness)
            .clickable { onClick() }
    ) {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "${report.month}의 기록",
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                color = DarkGray
            )
        }
    }
}
