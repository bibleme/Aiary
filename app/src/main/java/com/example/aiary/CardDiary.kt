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
import java.time.format.DateTimeFormatter
import androidx.compose.ui.res.painterResource
import coil.compose.AsyncImagePainter

private val White = Color(0xFFFFFFFF)

data class DiaryPhoto(
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
    var isFlipped by remember { mutableStateOf(false) }

    // 서버에서 받아온 데이터를 저장할 상태 변수들
    var diaryPhotos by remember { mutableStateOf<List<DiaryPhoto>>(emptyList()) }
    var fullDiaryText by remember { mutableStateOf("일기 내용을 불러오는 중입니다...") }
    var isLoading by remember { mutableStateOf(true) }

    // 화면이 처음 열릴 때 서버에서 데이터 가져오기
    LaunchedEffect(selectedDate) {
        try {
            val myId = UserSession.userId

            // 서버에서 전체 리스트 가져옴
            val listResponse = RetrofitClient.api.getDiaries(myId)

            if (listResponse.isSuccessful) {
                val allDiaries = listResponse.body() ?: emptyList()

                // [디버깅] 로그를 찍어서 확인해봅니다! (Logcat에서 "DIARY_DEBUG" 검색)
                Log.d("DIARY_DEBUG", "서버에서 가져온 개수: ${allDiaries.size}")
                if (allDiaries.isNotEmpty()) {
                    Log.d("DIARY_DEBUG", "서버 날짜 예시: ${allDiaries[0].created_at}")
                }

                // 선택한 날짜 변환 ("2025년 12월 11일" -> "2025-12-11")
                val targetDate = convertKoreanDateToIso(selectedDate)
                Log.d("DIARY_DEBUG", "내가 찾는 날짜: $targetDate")

                // 날짜 비교 (앞부분 10자리만 잘라서 비교)
                val filteredDiaries = allDiaries.filter { diary ->
                    // 서버 날짜가 "2025-12-11T..." 형태라면 앞 10글자("2025-12-11")만 자름
                    val serverDate = if (diary.created_at.length >= 10) diary.created_at.substring(0, 10) else diary.created_at
                    serverDate == targetDate
                }

                // UI용 데이터로 변환 
                diaryPhotos = filteredDiaries.map {

                    val fixedUrl = if (it.image_url.startsWith("http")) {
                        it.image_url
                    } else {
                        val baseUrl = "http://3.35.185.251:8000"
                        "$baseUrl${it.image_url}"
                    }

                    Log.d("DIARY_DEBUG", "원본: ${it.image_url} -> 수정후: $fixedUrl")

                    DiaryPhoto(fixedUrl, it.content)
                }

                // 사진이 있다면 줄글 요약 일기도 가져오기
                if (filteredDiaries.isNotEmpty()) {
                    Log.d("DIARY_DEBUG", "줄글 일기 요청 시작: ID=$myId, Date=$targetDate")

                    val summaryRequest = DaySummaryRequest(myId, targetDate)
                    val summaryResponse = RetrofitClient.api.createFullDiary(summaryRequest)

                    if (summaryResponse.isSuccessful) {
                        val result = summaryResponse.body()
                        Log.d("DIARY_DEBUG", "줄글 일기 응답 성공: ${result?.summary}")

                        fullDiaryText = result?.summary ?: "서버에서 빈 내용을 보냈습니다."
                    } else {
                        // 실패 원인을 로그에 출력
                        val errorMsg = summaryResponse.errorBody()?.string()
                        Log.e("DIARY_DEBUG", "줄글 일기 요청 실패! 코드: ${summaryResponse.code()}, 내용: $errorMsg")

                        fullDiaryText = "일기 생성 실패: ${summaryResponse.code()} (로그 확인 필요)"
                    }
                } else {
                    fullDiaryText = "작성된 일기가 없는 날입니다."
                }




            } else {
                Toast.makeText(context, "데이터를 불러오지 못했습니다.", Toast.LENGTH_SHORT).show()
            }
        } catch (e: Exception) {
            Log.e("CardDiary", "Error", e)
            fullDiaryText = "통신 오류가 발생했습니다."
        } finally {
            isLoading = false
        }
    }

    // Pager 설정
    val pagerState = rememberPagerState(pageCount = { diaryPhotos.size })
    val coroutineScope = rememberCoroutineScope()

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
                            FrontSideContent(diaryPhotos, pagerState, coroutineScope)
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
}

// AsyncImage 사용 (URL 이미지 로딩)
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun FrontSideContent(
    diaryPhotos: List<DiaryPhoto>,
    pagerState: androidx.compose.foundation.pager.PagerState,
    coroutineScope: CoroutineScope
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier.padding(16.dp)
    ) {
        Box(modifier = Modifier.fillMaxWidth().height(300.dp).clip(RoundedCornerShape(12.dp))) {
            HorizontalPager(state = pagerState) { page ->
                // Coil 라이브러리로 URL 이미지 로드
                AsyncImage(
                    model = diaryPhotos[page].imageUrl,
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize(),

                    // [1] 화면에 보여줄 이미지 설정 (버전 2 파라미터)
                    error = painterResource(id = android.R.drawable.ic_menu_report_image),
                    placeholder = painterResource(id = android.R.drawable.ic_menu_gallery),

                    // [2] onState 대신 onError 사용 (버전 2 파라미터)
                    onError = { state ->
                        // state가 이미 Error 타입이므로 타입 체크 불필요
                        Log.e("CoilError", "이미지 로드 실패: ${state.result.throwable.message}")
                    }
                )
            }

            if (pagerState.currentPage > 0) {
                IconButton(
                    onClick = { coroutineScope.launch { pagerState.animateScrollToPage(pagerState.currentPage - 1) } },
                    modifier = Modifier.align(Alignment.CenterStart).padding(8.dp).background(White.copy(0.7f),
                        CircleShape)
                ) { Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, null, tint = DarkGray) }
            }
            if (pagerState.currentPage < diaryPhotos.size - 1) {
                IconButton(
                    onClick = { coroutineScope.launch { pagerState.animateScrollToPage(pagerState.currentPage + 1) } },
                    modifier = Modifier.align(Alignment.CenterEnd).padding(8.dp).background(White.copy(0.7f),
                        CircleShape)
                ) { Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight,
                    null, tint = DarkGray) }
            }
        }
        Spacer(modifier = Modifier.height(20.dp))
        Text(
            text = diaryPhotos[pagerState.currentPage].comment,
            fontSize = 16.sp,
            color = DarkGray,
            textAlign = TextAlign.Center,
            fontWeight = FontWeight.Medium
        )
        Spacer(modifier = Modifier.height(10.dp))
    }
}

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

// 날짜 변환 헬퍼 함수
@RequiresApi(Build.VERSION_CODES.O)
fun convertKoreanDateToIso(koreanDate: String): String {
    return try {
        val simpleDate = koreanDate.split(" ").take(3).joinToString(" ")
        val formatter = DateTimeFormatter.ofPattern("yyyy년 M월 d일")
        val date = LocalDate.parse(simpleDate, formatter)
        date.toString() // "2025-12-10"
    } catch (e: Exception) {
        // 파싱 실패 시 오늘 날짜 반환하거나 에러 처리
        LocalDate.now().toString()
    }
}
