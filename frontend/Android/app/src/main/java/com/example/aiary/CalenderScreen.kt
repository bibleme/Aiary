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

    // 백엔드의 outdated 정책을 관리할 상태 변수들
    var isOutdated by remember { mutableStateOf(false) }
    var canRegenerate by remember { mutableStateOf(false) }
    var isRegenerating by remember { mutableStateOf(false) } // 버튼 로딩 상태

    var photoIdToDelete by remember { mutableStateOf<Int?>(null) }

    LaunchedEffect(selectedDate) {
        try {
            val myId = UserSession.userId
            val bearerToken = "Bearer ${UserSession.accessToken}"
            val listResponse = RetrofitClient.api.getDiaries(myId, bearerToken)

            if (listResponse.isSuccessful) {
                val allDiaries = listResponse.body() ?: emptyList()
                val targetDate = convertKoreanDateToIso(selectedDate)

                val filteredDiaries = allDiaries.filter { diary ->
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
                    Log.d("IMAGE_TEST", "S3 이미지 주소: $fixedUrl")
                    DiaryPhoto(id = it.id, imageUrl = fixedUrl, comment = it.content)
                }

                if (filteredDiaries.isNotEmpty()) {
                    val getResponse = RetrofitClient.api.getDailyDiary(targetDate, myId, bearerToken)

                    if (getResponse.isSuccessful && getResponse.body() != null) {
                        val body = getResponse.body()!!
                        fullDiaryText = body.content ?: "내용이 없습니다."
                        // 서버에서 outdated 상태 받아오기
                        isOutdated = body.is_outdated
                        canRegenerate = body.can_regenerate
                    } else {
                        val summaryRequest = DaySummaryRequest(myId, targetDate)
                        val createResponse = RetrofitClient.api.createDailyDiary(bearerToken, summaryRequest)

                        if (createResponse.isSuccessful && createResponse.body() != null) {
                            val body = createResponse.body()!!
                            fullDiaryText = body.content ?: "내용이 없습니다."
                            // 생성 시점의 상태 저장
                            isOutdated = body.is_outdated
                            canRegenerate = body.can_regenerate
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
            Column(
                modifier = Modifier.weight(1f).fillMaxWidth(),
                verticalArrangement = Arrangement.Center
            ) {
                // outdated 상태일 때 띄워줄 재생성 배너
                if (isOutdated && canRegenerate) {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF9C4)),
                        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp)
                    ) {
                        Row(
                            modifier = Modifier.padding(16.dp).fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text("새로운 기록이 있어요! 📝", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                Text("다시 생성하면 새 사진도 일기에 반영돼요.", fontSize = 12.sp, color = Color.DarkGray)
                            }

                            Button(
                                onClick = {
                                    coroutineScope.launch {
                                        isRegenerating = true
                                        try {
                                            val targetDate = convertKoreanDateToIso(selectedDate)
                                            val bearerToken = "Bearer ${UserSession.accessToken}"
                                            val response = RetrofitClient.api.regenerateDailyDiary(targetDate, bearerToken)

                                            if (response.isSuccessful && response.body() != null) {
                                                val updatedBody = response.body()!!
                                                fullDiaryText = updatedBody.content ?: fullDiaryText
                                                isOutdated = updatedBody.is_outdated
                                                canRegenerate = updatedBody.can_regenerate
                                                Toast.makeText(context, "새로운 기록으로 일기가 완성되었어요!", Toast.LENGTH_SHORT).show()
                                            } else {
                                                Toast.makeText(context, "재생성 실패: ${response.code()}", Toast.LENGTH_SHORT).show()
                                            }
                                        } catch (e: Exception) {
                                            Toast.makeText(context, "통신 오류가 발생했습니다.", Toast.LENGTH_SHORT).show()
                                        } finally {
                                            isRegenerating = false
                                        }
                                    }
                                },
                                enabled = !isRegenerating,
                                colors = ButtonDefaults.buttonColors(containerColor = PrimaryBlue),
                                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                            ) {
                                if (isRegenerating) {
                                    CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.White, strokeWidth = 2.dp)
                                } else {
                                    Text("다시 생성 ✨", fontSize = 12.sp, color = Color.White)
                                }
                            }
                        }
                    }
                }

                // 기존 플립 카드 영역
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
                                onDeleteClick = { id -> photoIdToDelete = id }
                            )
                        } else {
                            BackSideContent(
                                fullDiaryText = fullDiaryText,
                                onSaveClick = { updatedText ->
                                    fullDiaryText = updatedText
                                    coroutineScope.launch {
                                        try {
                                            val bearerToken = "Bearer ${UserSession.accessToken}"
                                            val targetDate = convertKoreanDateToIso(selectedDate)
                                            val request = UpdateDiaryContentRequest(content = updatedText)
                                            val response = RetrofitClient.api.updateDailyDiary(targetDate, bearerToken, request)

                                            if (response.isSuccessful) {
                                                Toast.makeText(context, "일기가 수정되었습니다!", Toast.LENGTH_SHORT).show()
                                            } else {
                                                Toast.makeText(context, "수정 실패: ${response.code()}", Toast.LENGTH_SHORT).show()
                                            }
                                        } catch (e: Exception) {
                                            Toast.makeText(context, "통신 오류가 발생했습니다.", Toast.LENGTH_SHORT).show()
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

    // 기존 삭제 팝업 영역
    if (photoIdToDelete != null) {
        AlertDialog(
            onDismissRequest = { photoIdToDelete = null },
            containerColor = Color.White,
            title = { Text("기록 삭제", fontWeight = FontWeight.Bold) },
            text = { Text("이 사진과 기록을 정말 삭제하시겠습니까?\n(복구할 수 없습니다.)") },
            confirmButton = {
                TextButton(
                    onClick = {
                        val deleteId = photoIdToDelete!!
                        photoIdToDelete = null
                        isLoading = true

                        coroutineScope.launch {
                            try {
                                val myId = UserSession.userId
                                val bearerToken = "Bearer ${UserSession.accessToken}"
                                val targetDate = convertKoreanDateToIso(selectedDate)

                                val response = RetrofitClient.api.deleteDiary(deleteId, myId, bearerToken)

                                if (response.isSuccessful) {
                                    Toast.makeText(context, "사진이 삭제되었습니다.", Toast.LENGTH_SHORT).show()
                                    diaryPhotos = diaryPhotos.filter { it.id != deleteId }

                                    if (diaryPhotos.isNotEmpty()) {
                                        val getResponse = RetrofitClient.api.getDailyDiary(targetDate, myId, bearerToken)

                                        if (getResponse.isSuccessful && getResponse.body() != null) {
                                            val getBody = getResponse.body()!!
                                            fullDiaryText = getBody.content ?: fullDiaryText

                                            // 사진 개수가 달라졌으므로 백엔드가 is_outdated = true 를 줌
                                            // 이 값이 true로 바뀌면서 화면에 노란색 재생성 배너가 나타남
                                            isOutdated = getBody.is_outdated
                                            canRegenerate = getBody.can_regenerate
                                        }
                                    } else {
                                        // 남은 사진이 0장이면 일기도 비워줍니다.
                                        fullDiaryText = "작성된 일기가 없는 날입니다."
                                        isOutdated = false
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
                ) { Text("삭제", color = Color.Red, fontWeight = FontWeight.Bold) }
            },
            dismissButton = {
                TextButton(onClick = { photoIdToDelete = null }) { Text("취소", color = Color.Gray) }
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
                // 예외 처리
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



// 저장 버튼을 눌렀을 때 실행할 행동을 전달받도록 변경
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
                        onSaveClick(editedText) 
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
                    .weight(1f), 
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
