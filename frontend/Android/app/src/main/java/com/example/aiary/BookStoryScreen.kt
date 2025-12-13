package com.example.aiary

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.ClickableText
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.aiary.data.StoryBookData
import com.example.aiary.data.StoryEvent

val BookCoverGreen = Color(0xFF5F8565)
val BookInsideBg = Color(0xFFF0F0F0)
val KeywordBlue = Color(0xFF4A90E2)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BookStoryScreen(
    storyData: StoryBookData,
    onBack: () -> Unit
) {
    var selectedEvent by remember { mutableStateOf<StoryEvent?>(null) }
    var isDialogOpen by remember { mutableStateOf(false) }
    // 카드가 뒤집혔는지 여부 (false: 앞면, true: 뒷면)
    var isFlipped by remember { mutableStateOf(false) }

    // 회전 각도 애니메이션
    val rotation by animateFloatAsState(
        targetValue = if (isFlipped) 180f else 0f,
        animationSpec = tween(durationMillis = 500),
        label = "flipAnimation"
    )

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("Book Type", fontWeight = FontWeight.Bold, color = DarkGray) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "뒤로", tint = DarkGray)
                    }
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(containerColor = BackgroundBeige)
            )
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(BackgroundBeige)
                .padding(16.dp),
            contentAlignment = Alignment.Center
        ) {
            // 카드 전체 영역
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(0.7f) // 책 비율 설정
                    .graphicsLayer {
                        rotationY = rotation // Y축 기준으로 회전
                        cameraDistance = 12f * density // 원근감 효과
                    }
                    .clickable { isFlipped = !isFlipped } // 클릭 시 뒤집기 상태 토글
            ) {
                if (rotation <= 90f) {
                    // 앞면 (Cover) 표시
                    BookCover(
                        storyData = storyData,
                        modifier = Modifier.fillMaxSize()
                    )
                } else {
                    // 뒷면 (Inside) 표시
                    // 뒷면은 좌우가 반전되어 보이므로 다시 반전시켜서 정상적으로 보이게 함
                    BookInside(
                        storyData = storyData,
                        onEventClick = { event ->
                            selectedEvent = event
                            isDialogOpen = true
                        },
                        modifier = Modifier
                            .fillMaxSize()
                            .graphicsLayer { rotationY = 180f }
                    )
                }
            }
        }

        // 팝업 다이얼로그
        if (isDialogOpen && selectedEvent != null) {
            BookPictureDialog(
                event = selectedEvent!!,
                onDismiss = {
                    isDialogOpen = false
                    selectedEvent = null
                }
            )
        }
    }
}

@Composable
fun BookCover(storyData: StoryBookData, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            // 메인 사진
            AsyncImage(
                model = storyData.mainPhotoUrl,
                contentDescription = "Main Photo",
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .weight(1f) // 남은 공간을 모두 사진이 차지
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(Color.LightGray)
            )

            Spacer(modifier = Modifier.height(16.dp))

            // 월 표시 바
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(60.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(BookCoverGreen),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = storyData.month,
                    color = Color.White,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}

@Composable
fun BookInside(
    storyData: StoryBookData,
    onEventClick: (StoryEvent) -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp),
        colors = CardDefaults.cardColors(containerColor = BookInsideBg)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = storyData.month,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = DarkGray,
                modifier = Modifier
                    .align(Alignment.Start)
                    .padding(bottom = 16.dp)
            )

            // 요약글 (특정 단어 클릭 가능하게 처리)
            val annotatedString = buildAnnotatedString {
                var currentIndex = 0
                val sortedEvents = storyData.events.sortedBy { storyData.summary.indexOf(it.keyword) }

                for (event in sortedEvents) {
                    val startIndex = storyData.summary.indexOf(event.keyword, currentIndex)
                    if (startIndex >= 0) {
                        append(storyData.summary.substring(currentIndex, startIndex))
                        pushStringAnnotation(tag = "EVENT", annotation = event.keyword)
                        withStyle(style = SpanStyle(color = KeywordBlue, fontWeight = FontWeight.Bold)) {
                            append(event.keyword)
                        }
                        pop()
                        currentIndex = startIndex + event.keyword.length
                    }
                }
                if (currentIndex < storyData.summary.length) {
                    append(storyData.summary.substring(currentIndex))
                }
            }

            ClickableText(
                text = annotatedString,
                style = LocalTextStyle.current.copy(
                    fontSize = 18.sp,
                    lineHeight = 28.sp,
                    color = DarkGray
                ),
                onClick = { offset ->
                    annotatedString.getStringAnnotations(tag = "EVENT", start = offset, end = offset)
                        .firstOrNull()?.let { annotation ->
                            storyData.events.find { it.keyword == annotation.item }?.let { event ->
                                onEventClick(event)
                            }
                        }
                }
            )
        }
    }
}

@Composable
fun BookPictureDialog(
    event: StoryEvent,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = BookInsideBg,
        title = {
            Text(text = event.description, fontWeight = FontWeight.Bold, fontSize = 18.sp)
        },
        text = {
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.heightIn(max = 400.dp) // 팝업 최대 높이 제한
            ) {
                items(event.photoUrls) { photoUrl ->
                    AsyncImage(
                        model = photoUrl,
                        contentDescription = event.keyword,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(200.dp)
                            .clip(RoundedCornerShape(8.dp))
                            .background(Color.LightGray)
                    )
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("닫기", color = KeywordBlue, fontWeight = FontWeight.Bold)
            }
        }
    )
}

// 나중에 수정
@Preview(showBackground = true)
@Composable
fun BookStoryScreenPreview() {
    val sampleData = StoryBookData(
        month = "2025.02",
        mainPhotoUrl = "https://picsum.photos/id/1011/400/400",
        summary = """
            이번 한 달은 사소한 변화들이 모여 아이의 성장을 또렷하게 보여준 시간이었다.
            
            손에 쥐는 힘이 한층 단단해지고, 배밀이·앉기·놀이 같은 작은 시도들이 눈에 띄게 늘었다.
            
            표정도 한결 다양해져 웃음도, 호기심 어린 집중도, 새로운 환경에 대한 설렘도 자주 드러났다.
        """.trimIndent(),
        events = listOf(
            StoryEvent("배밀이", listOf("https://picsum.photos/id/1025/400/300"), "아이의 배밀이 사진"),
            StoryEvent("앉기", listOf("https://picsum.photos/id/1005/400/300"), "혼자 앉아있는 모습"),
            StoryEvent("놀이", listOf("https://picsum.photos/id/1016/400/300"), "장난감 가지고 노는 시간")
        )
    )
    BookStoryScreen(storyData = sampleData, onBack = {})
}
