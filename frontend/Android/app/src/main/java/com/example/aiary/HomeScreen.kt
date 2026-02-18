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
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.clickable
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable

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
                            //    .background(White)
                            //    .border(6.dp, White, CircleShape)
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
                            val response = RetrofitClient.api.getDiaries(myId)
                            if (response.isSuccessful) {
                                val diaries = response.body() ?: emptyList()

                                if (diaries.isNotEmpty()) {
                                    // 서버에서 온 일기들을 "YYYY.MM" (예: 2025.12) 단위로 그룹화(묶기) 합니다.
                                    val groupedDiaries = diaries.groupBy { diary ->
                                        if (diary.created_at.length >= 7) {
                                            // "2025-12-11T..." -> "2025-12" -> "2025.12"
                                            diary.created_at.substring(0, 7).replace("-", ".")
                                        } else {
                                            "알 수 없음"
                                        }
                                    }

                                    val tempReportList = mutableListOf<StoryBookData>()
                                    val tempPhotosMap = mutableMapOf<String, List<String>>()

                                    // 묶여진 월별 일기들을 바탕으로 진짜 책(리포트)을 만듭니다.
                                    for ((monthStr, monthDiaries) in groupedDiaries) {
                                        // 해당 월의 모든 사진 주소 정리
                                        val photoUrls = monthDiaries.map { diary ->
                                            if (diary.image_url.startsWith("http")) diary.image_url
                                            else "http://3.35.185.251:8000${diary.image_url}"
                                        }
                                        tempPhotosMap[monthStr] = photoUrls

                                        // 해당 월의 이벤트 추출
                                        val events = monthDiaries.take(3).map { diary ->
                                            val fixedEventUrl = if (diary.image_url.startsWith("http")) diary.image_url else "http://3.35.185.251:8000${diary.image_url}"
                                            StoryEvent("기록", listOf(fixedEventUrl), diary.content)
                                        }

                                        // 리포트 1권 완성!
                                        tempReportList.add(
                                            StoryBookData(
                                                month = monthStr, // "2025.12" 등
                                                mainPhotoUrl = photoUrls.last(), // 가장 최근 사진을 표지로
                                                summary = "${monthStr}의 소중한 추억들입니다. (총 ${monthDiaries.size}개의 기록)", // 임시 요약글
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
                            onBack = { selectedReport = null },
                            onMainPhotoChanged = { newUrl ->
                                selectedReport = selectedReport!!.copy(mainPhotoUrl = newUrl)
                                reportList = reportList.map { report ->
                                    if (report.month == selectedReport!!.month) report.copy(mainPhotoUrl = newUrl)
                                    else report
                                }
                            }
                        )
                    }
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

@Composable
fun ReportListScreen(
    reports: List<StoryBookData>, // 리포트 목록 데이터
    onReportClick: (StoryBookData) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundBeige)
            .padding(24.dp)
    ) {
        Text(
            text = "추억 보관함 📚",
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            color = DarkGray,
            modifier = Modifier.padding(bottom = 24.dp)
        )

        if (reports.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("아직 생성된 리포트가 없어요.", color = Color.Gray)
            }
        } else {
            // 2칸짜리 격자 모양 책장
            LazyVerticalGrid(
                columns = GridCells.Fixed(2),
                horizontalArrangement = Arrangement.spacedBy(16.dp),
                verticalArrangement = Arrangement.spacedBy(24.dp)
            ) {
                items(reports) { report ->
                    ReportItem(report = report, onClick = { onReportClick(report) })
                }
            }
        }
    }
}

@Composable
fun ReportItem(
    report: StoryBookData,
    onClick: () -> Unit
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .clickable { onClick() }
    ) {
        // 책 표지 모양 (그림자 효과)
        Card(
            shape = RoundedCornerShape(8.dp), // 책은 둥근 모서리가 적게
            elevation = CardDefaults.cardElevation(defaultElevation = 6.dp),
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(0.7f) // 책 비율 (세로로 긴 형태)
        ) {
            Box(modifier = Modifier.fillMaxSize()) {
                AsyncImage(
                    model = report.mainPhotoUrl,
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize()
                )
                // 책등 효과 (왼쪽에 살짝 음영을 줘서 책처럼 보이게 함)
                Box(
                    modifier = Modifier
                        .fillMaxHeight()
                        .width(6.dp)
                        .background(Color.Black.copy(alpha = 0.2f))
                        .align(Alignment.CenterStart)
                )
            }
        }
        Spacer(modifier = Modifier.height(8.dp))
        // 연월 표시 (예: 2025.12)
        Text(
            text = report.month,
            fontSize = 16.sp,
            fontWeight = FontWeight.Bold,
            color = DarkGray
        )
    }
}
