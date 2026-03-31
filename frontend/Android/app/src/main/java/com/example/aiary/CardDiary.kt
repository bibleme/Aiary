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
import androidx.compose.material.icons.filled.Edit
import com.example.aiary.data.UpdateDiaryContentRequest

private val White = Color(0xFFFFFFFF)

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
            val bearerToken = "Bearer ${UserSession.accessToken}"
            val listResponse = RetrofitClient.api.getDiaries(myId, bearerToken)

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
                    // 서버에서 받아온 id를 함께 저장 
                    DiaryPhoto(id = it.id, imageUrl = fixedUrl, comment = it.content)
                }

                if (filteredDiaries.isNotEmpty()) {
                    // 먼저 서버에 이미 만들어진 요약 일기가 있는지 '조회(GET)' 해봅니다.
                    // (주의: ApiService.kt에 getDailyDiary가 선언되어 있어야 합니다!)
                    val getResponse = RetrofitClient.api.getDailyDiary(targetDate, myId, bearerToken)

                    if (getResponse.isSuccessful && getResponse.body() != null) {
                        // 저장된 일기가 있다면? 그걸 그대로 꺼내서 보여줍니다! (일기가 매번 바뀌지 않게 됨)
                        fullDiaryText = getResponse.body()?.content ?: "내용이 없습니다."
                    } else {
                        // 조회했는데 없다면? (처음 들어온 상태) -> 이때만 새로 '생성(POST)' 요청을 보냅니다!
                        val summaryRequest = DaySummaryRequest(myId, targetDate)
                        val createResponse = RetrofitClient.api.createDailyDiary(bearerToken, summaryRequest)

                        if (createResponse.isSuccessful) {
                            fullDiaryText = createResponse.body()?.content ?: "내용이 없습니다."
                        } else {
                            fullDiaryText = "일기 생성 실패: ${createResponse.code()}"
                        }
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
                            BackSideContent(
                                fullDiaryText = fullDiaryText,
                                onSaveClick = { updatedText ->
                                    fullDiaryText = updatedText

                                    // 서버에 수정된 글을 전송
                                    coroutineScope.launch {
                                        try {
                                            // 토큰이랑 날짜 준비
                                            val bearerToken = "Bearer ${UserSession.accessToken}"
                                            val targetDate = convertKoreanDateToIso(selectedDate)

                                            // 방금 만든 포장 박스에 바뀐 글씨 담기
                                            val request = UpdateDiaryContentRequest(content = updatedText)

                                            // ApiService 호출!
                                            val response = RetrofitClient.api.updateDailyDiary(targetDate,
                                                bearerToken, request)

                                            if (response.isSuccessful) {
                                                Toast.makeText(context, "일기가 수정되었습니다!",
                                                    Toast.LENGTH_SHORT).show()
                                            } else {
                                                Toast.makeText(context, "수정 실패: ${response.code()}",
                                                    Toast.LENGTH_SHORT).show()
                                            }
                                        } catch (e: Exception) {
                                            Toast.makeText(context, "통신 오류가 발생했습니다.",
                                                Toast.LENGTH_SHORT).show()
                                        }
                                    }
                                }
                            )
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
                        photoIdToDelete = null 
                        isLoading = true

                        // 서버에 삭제 요청
                        coroutineScope.launch {
                            try {
                                val myId = UserSession.userId
                                val bearerToken = "Bearer ${UserSession.accessToken}"
                                val response = RetrofitClient.api.deleteDiary(deleteId, myId, bearerToken)

                                if (response.isSuccessful) {
                                    Toast.makeText(context, "사진이 삭제되었습니다.", Toast.LENGTH_SHORT).show()
                                    // 🗑️ 방금 지운 사진을 화면(리스트)에서 제거
                                    diaryPhotos = diaryPhotos.filter { it.id != deleteId }

                                    // 사진을 지웠으니 일기도 재생성 요청!
                                    if (diaryPhotos.isNotEmpty()) {
                                        val targetDate = convertKoreanDateToIso(selectedDate)
                                        val regenResponse = RetrofitClient.api.regenerateDailyDiary(targetDate, bearerToken)

                                        if (regenResponse.isSuccessful && regenResponse.body() != null) {
                                            // 재생성된 새 일기로 화면 글씨 업데이트!
                                            fullDiaryText = regenResponse.body()?.content ?: fullDiaryText
                                            Toast.makeText(context, "남은 사진에 맞게 일기가 다시 작성되었습니다!",
                                                Toast.LENGTH_SHORT).show()
                                        }
                                    } else {
                                        // 사진이 0장이 되면 일기도 비워주기
                                        fullDiaryText = "작성된 일기가 없는 날입니다."
                                    }

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

            // 휴지통(삭제) 버튼 (우측 상단)
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

            // 이전 / 다음 버튼 
            if (pagerState.currentPage > 0) {
                IconButton(
                    onClick = { coroutineScope.launch { pagerState.animateScrollToPage(pagerState.currentPage - 1) } },
                    modifier = Modifier.align(Alignment.CenterStart).padding(8.dp)
                        .background(White.copy(0.7f), CircleShape)
                ) { Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, null, tint = DarkGray) }
            }
            if (pagerState.currentPage < diaryPhotos.size - 1) {
                IconButton(
                    onClick = { coroutineScope.launch { pagerState.animateScrollToPage(pagerState.currentPage + 1) } },
                    modifier = Modifier.align(Alignment.CenterEnd).padding(8.dp)
                        .background(White.copy(0.7f), CircleShape)
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



// 저장 버튼을 눌렀을 때 실행할 행동(onSaveClick)을 전달받도록 변경
@Composable
fun BackSideContent(
    fullDiaryText: String,
    onSaveClick: (String) -> Unit
) {
    // 수정 모드 상태와 현재 적힌 글씨를 기억하는 변수
    var isEditing by remember { mutableStateOf(false) }
    var editedText by remember { mutableStateOf(fullDiaryText) }

    // 서버에서 일기 내용을 새로 불러오면 편집창 글씨도 업데이트
    LaunchedEffect(fullDiaryText) {
        editedText = fullDiaryText
    }

    Column(
        modifier = Modifier
            .padding(24.dp)
            .heightIn(min = 350.dp, max = 500.dp)
    ) {
        // --- 윗부분: 제목과 수정/저장 버튼 ---
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "오늘의 전체 기록",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = PrimaryBlue
            )

            if (isEditing) {
                Row {
                    TextButton(onClick = {
                        isEditing = false
                        editedText = fullDiaryText // 취소하면 원래 내용으로 복구
                    }) {
                        Text("취소", color = Color.Gray)
                    }
                    TextButton(onClick = {
                        onSaveClick(editedText) // 부모 화면으로 수정된 텍스트 전달
                        isEditing = false
                    }) {
                        Text("저장", color = PrimaryBlue, fontWeight = FontWeight.Bold)


                    }
                }
            } else {
                IconButton(onClick = { isEditing = true }, modifier = Modifier.size(24.dp)) {
                    Icon(Icons.Default.Edit, contentDescription = "수정하기", tint = Color.Gray)
                }
            }
        }

        // 아랫부분: 일기 내용 or 텍스트 입력창
        if (isEditing) {
            OutlinedTextField(
                value = editedText,
                onValueChange = { editedText = it },
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f), // 남은 공간을 꽉 채우도록
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = PrimaryBlue,
                    unfocusedBorderColor = Color.LightGray
                )
            )
        } else {
            Text(
                text = fullDiaryText,
                fontSize = 15.sp,
                color = DarkGray,
                modifier = Modifier.verticalScroll(rememberScrollState())
            )
        }
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
