package com.example.aiary

import android.os.Build
import android.util.Log
import android.widget.Toast
import androidx.annotation.RequiresApi
import androidx.compose.animation.Crossfade
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Delete // 👇 [추가] 휴지통 아이콘
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.aiary.data.DaySummaryRequest
import com.example.aiary.data.UserSession
import com.example.aiary.network.RetrofitClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch
import java.time.LocalDate
import androidx.compose.ui.res.painterResource

private val White = Color(0xFFFFFFFF)

// 삭제를 위해 서버의 고유 ID(id)를 추가로 받습니다.
data class DiaryPhoto(
    val id: Int,
    val imageUrl: String,
    val comment: String
)

@RequiresApi(Build.VERSION_CODES.O)
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun CardDiaryScreen(
    selectedDate: String,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    var isFlipped by remember { mutableStateOf(false) }

    var diaryPhotos by remember { mutableStateOf<List<DiaryPhoto>>(emptyList()) }
    var fullDiaryText by remember { mutableStateOf("일기 내용을 불러오는 중입니다...") }
    var isLoading by remember { mutableStateOf(true) }

    // 삭제할 일기 ID를 임시로 저장하는 변수 (null이면 팝업 안 뜸)
    var photoIdToDelete by remember { mutableStateOf<Int?>(null) }

    // 화면이 처음 열릴 때 데이터 가져오기
    LaunchedEffect(selectedDate) {
        try {
            val myId = UserSession.userId
            val listResponse = RetrofitClient.api.getDiaries(myId)

            if (listResponse.isSuccessful) {
                val allDiaries = listResponse.body() ?: emptyList()
                val targetDate = convertKoreanDateToIso(selectedDate)

                /*val filteredDiaries = allDiaries.filter { diary ->
                    val serverDate = if (diary.created_at.length >= 10) diary.created_at.substring(0, 10) else diary.created_at
                    serverDate == targetDate*/
                val filteredDiaries = allDiaries.filter { diary ->
                    // 1순위: diary_date가 있으면 그걸 쓴다.
                    // 2순위: 없으면(옛날 일기면) created_at(작성시간) 앞 10자리를 쓴다.
                    val realDate = diary.diary_date ?: diary.created_at.take(10)

                    realDate == targetDate
                }

                diaryPhotos = filteredDiaries.map {
                    val fixedUrl = if (it.image_url.startsWith("http")) {
                        it.image_url
                    } else {
                        val baseUrl = "http://3.35.185.251:8000"
                        "$baseUrl${it.image_url}"
                    }
                    // 서버에서 받아온 id를 함께 저장 (서버 데이터 클래스에 id가 있어야 함!)
                    DiaryPhoto(id = it.id, imageUrl = fixedUrl, comment = it.content)
                }

                if (filteredDiaries.isNotEmpty()) {
                    val summaryRequest = DaySummaryRequest(myId, targetDate)
                    val summaryResponse = RetrofitClient.api.createFullDiary(summaryRequest)

                    if (summaryResponse.isSuccessful) {
                        fullDiaryText = summaryResponse.body()?.full_diary ?: "내용이 없습니다."
                    } else {
                        fullDiaryText = "일기 생성 실패: ${summaryResponse.code()}"
                    }
                } else {
                    fullDiaryText = "작성된 일기가 없는 날입니다."
                }
            } else {
                Toast.makeText(context, "데이터를 불러오지 못했습니다.", Toast.LENGTH_SHORT).show()
            }
        } catch (e: Exception) {
            fullDiaryText = "통신 오류가 발생했습니다."
        } finally {
            isLoading = false
        }
    }

    // Pager 설정 (사진 개수가 바뀌면 Pager도 업데이트됨)
    val pagerState = rememberPagerState(pageCount = { diaryPhotos.size })

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundBeige)
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // 상단 네비게이션
        Row(
            modifier = Modifier.fillMaxWidth().padding(bottom = 24.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = { onBack() }) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "뒤로", tint = DarkGray)
            }
            Text(
                text = selectedDate,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = DarkGray,
                modifier = Modifier.weight(1f),
                textAlign = TextAlign.Center
            )
            Spacer(modifier = Modifier.size(48.dp))
        }

        if (isLoading) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = PrimaryBlue)
            }
        } else if (diaryPhotos.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("작성된 일기가 없습니다 텅~ 🗑️", color = Color.Gray)
            }
        } else {
            // 카드 영역
            Column(
                modifier = Modifier.weight(1f).fillMaxWidth(),
                verticalArrangement = Arrangement.Center
            ) {
                Card(
                    colors = CardDefaults.cardColors(containerColor = White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 8.dp),
                    shape = RoundedCornerShape(16.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .wrapContentHeight()
                        .clickable { isFlipped = !isFlipped }
                ) {
                    Crossfade(targetState = isFlipped, label = "FlipAnimation") { flipped ->
                        if (!flipped) {
                            FrontSideContent(
                                diaryPhotos = diaryPhotos,
                                pagerState = pagerState,
                                coroutineScope = coroutineScope,
                                onDeleteClick = { id ->
                                    // 휴지통 버튼 누르면 삭제할 ID를 저장하고 팝업을 띄움
                                    photoIdToDelete = id
                                }
                            )
                        } else {
                            BackSideContent(fullDiaryText)
                        }
                    }
                }

                if (!isFlipped) {
                    Spacer(modifier = Modifier.height(10.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center
                    ) {
                        (0 until diaryPhotos.size).forEach { index ->
                            Box(
                                modifier = Modifier
                                    .padding(horizontal = 3.dp)
                                    .size(8.dp)
                                    .clip(CircleShape)
                                    .background(if (pagerState.currentPage == index) PrimaryBlue else Color.LightGray)
                            )
                        }
                    }
                }
            }
        }
    }

    // 삭제 확인 팝업
    if (photoIdToDelete != null) {
        AlertDialog(
            onDismissRequest = { photoIdToDelete = null }, // 취소하면 팝업 닫기
            containerColor = Color.White,
            title = { Text("기록 삭제", fontWeight = FontWeight.Bold) },
            text = { Text("이 사진과 기록을 정말 삭제하시겠습니까?\n(복구할 수 없습니다.)") },
            confirmButton = {
                TextButton(
                    onClick = {
                        val deleteId = photoIdToDelete!!
                        photoIdToDelete = null // 팝업 닫기
                        isLoading = true

                        // 서버에 삭제 요청
                        coroutineScope.launch {
                            try {
                                val myId = UserSession.userId
                                val response = RetrofitClient.api.deleteDiary(deleteId, myId) 
                                if (response.isSuccessful) {
                                    Toast.makeText(context, "삭제되었습니다.", Toast.LENGTH_SHORT).show()
                                    // 방금 지운 사진을 내 폰 화면(리스트)에서도 제거
                                    diaryPhotos = diaryPhotos.filter { it.id != deleteId }
                                } else {
                                    Toast.makeText(context, "삭제 실패: ${response.code()}", Toast.LENGTH_SHORT).show()
                                }
                            } catch (e: Exception) {
                                Toast.makeText(context, "오류가 발생했습니다.", Toast.LENGTH_SHORT).show()
                            } finally {
                                isLoading = false
                            }
                        }
                    }
                ) {
                    Text("삭제", color = Color.Red, fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { photoIdToDelete = null }) {
                    Text("취소", color = Color.Gray)
                }
            }
        )
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun FrontSideContent(
    diaryPhotos: List<DiaryPhoto>,
    pagerState: androidx.compose.foundation.pager.PagerState,
    coroutineScope: CoroutineScope,
    onDeleteClick: (Int) -> Unit
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier.padding(16.dp)
    ) {
        Box(modifier = Modifier.fillMaxWidth().height(300.dp).clip(RoundedCornerShape(12.dp))) {
            HorizontalPager(state = pagerState) { page ->
                // 예외 처리 (리스트 크기가 바뀌었을 때 안전하게)
                if (page < diaryPhotos.size) {
                    AsyncImage(
                        model = diaryPhotos[page].imageUrl,
                        contentDescription = null,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize(),
                        error = painterResource(id = android.R.drawable.ic_menu_report_image),
                        placeholder = painterResource(id = android.R.drawable.ic_menu_gallery)
                    )
                }
            }

            // 👇 휴지통(삭제) 버튼 (우측 상단)
            if (diaryPhotos.isNotEmpty()) {
                IconButton(
                    // 현재 보고 있는 페이지의 ID를 넘겨줍니다.
                    onClick = { onDeleteClick(diaryPhotos[pagerState.currentPage].id) },
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(8.dp)
                        .size(36.dp)
                        .background(Color.Black.copy(alpha = 0.5f), CircleShape)
                ) {
                    Icon(
                        imageVector = Icons.Default.Delete,
                        contentDescription = "삭제",
                        tint = Color.White,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }

            // 이전 / 다음 버튼 (기존 코드 유지)
            if (pagerState.currentPage > 0) {
                IconButton(
                    onClick = { coroutineScope.launch { pagerState.animateScrollToPage(pagerState.currentPage - 1) } },
                    modifier = Modifier.align(Alignment.CenterStart).padding(8.dp).background(White.copy(0.7f), CircleShape)
                ) { Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, null, tint = DarkGray) }
            }
            if (pagerState.currentPage < diaryPhotos.size - 1) {
                IconButton(
                    onClick = { coroutineScope.launch { pagerState.animateScrollToPage(pagerState.currentPage + 1) } },
                    modifier = Modifier.align(Alignment.CenterEnd).padding(8.dp).background(White.copy(0.7f), CircleShape)
                ) { Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, null, tint = DarkGray) }
            }
        }
        Spacer(modifier = Modifier.height(20.dp))

        // 현재 페이지의 코멘트
        if (diaryPhotos.isNotEmpty() && pagerState.currentPage < diaryPhotos.size) {
            Text(
                text = diaryPhotos[pagerState.currentPage].comment,
                fontSize = 16.sp,
                color = DarkGray,
                textAlign = TextAlign.Center,
                fontWeight = FontWeight.Medium
            )
        }
        Spacer(modifier = Modifier.height(10.dp))
    }
}

// BackSideContent 및 날짜 변환 함수는 기존 코드와 동일하게 유지합니다.
@Composable
fun BackSideContent(fullDiaryText: String) {
    Column(
        modifier = Modifier
            .padding(24.dp)
            .heightIn(min = 350.dp, max = 500.dp)
    ) {
        Text(
            text = "오늘의 전체 기록",
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            color = PrimaryBlue,
            modifier = Modifier.padding(bottom = 12.dp)
        )
        Text(
            text = fullDiaryText,
            fontSize = 15.sp,
            color = DarkGray,
            modifier = Modifier.verticalScroll(rememberScrollState())
        )
    }
}

@RequiresApi(Build.VERSION_CODES.O)
fun convertKoreanDateToIso(inputDate: String): String {
    try {
        val numbers = Regex("\\d+").findAll(inputDate).map { it.value.toInt() }.toList()
        if (numbers.size >= 3) {
            val year = numbers[0]
            val month = numbers[1]
            val day = numbers[2]
            return String.format("%04d-%02d-%02d", year, month, day)
        }
    } catch (e: Exception) {
        Log.e("DateConvert", "날짜 변환 실패", e)
    }
    return LocalDate.now().toString()
}
