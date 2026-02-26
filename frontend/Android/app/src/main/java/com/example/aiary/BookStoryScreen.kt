package com.example.aiary

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.ClickableText
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Edit
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

// 앱 테마 색상 (파란색)
// val PrimaryBlue = Color(0xFF87CEFA)
val BookInsideBg = Color(0xFFF0F0F0)
val KeywordBlue = Color(0xFF4A90E2)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BookStoryScreen(
    storyData: StoryBookData,
    allMonthPhotoUrls: List<String>, // [추가] 그 달의 모든 사진 리스트를 받아옴
    onBack: () -> Unit,
    onMainPhotoChanged: (String) -> Unit
) {
    // [추가] 현재 선택된 메인 사진 (초기값은 데이터의 mainPhotoUrl)
    var currentMainPhoto by remember { mutableStateOf(storyData.mainPhotoUrl) }

    // [추가] 사진 변경 팝업 열림 여부
    var isPhotoPickerOpen by remember { mutableStateOf(false) }

    var selectedEvent by remember { mutableStateOf<StoryEvent?>(null) }
    var isEventDialogOpen by remember { mutableStateOf(false) }
    var isFlipped by remember { mutableStateOf(false) }

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
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "뒤로",
                            tint = DarkGray)
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
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(0.7f)
                    .graphicsLayer {
                        rotationY = rotation
                        cameraDistance = 12f * density
                    }
            ) {
                if (rotation <= 90f) {
                    BookCover(
                        mainPhotoUrl = currentMainPhoto,
                        month = storyData.month,
                        onEditClick = { isPhotoPickerOpen = true },
                        // 👇 [추가] 책을 뒤집는 행동을 넘겨줍니다.
                        onFlipClick = { isFlipped = !isFlipped },
                        modifier = Modifier.fillMaxSize()
                    )
                } else {
                    BookInside(
                        storyData = storyData,
                        onEventClick = { event ->
                            selectedEvent = event
                            isEventDialogOpen = true
                        },
                        // 👇 [추가] 여기도 뒤집는 행동을 넘겨줍니다.
                        onFlipClick = { isFlipped = !isFlipped },
                        modifier = Modifier
                            .fillMaxSize()
                            .graphicsLayer { rotationY = 180f }
                    )
                }
            }
        }

        // 이벤트 상세 팝업
        if (isEventDialogOpen && selectedEvent != null) {
            BookPictureDialog(
                event = selectedEvent!!,
                onDismiss = {
                    isEventDialogOpen = false
                    selectedEvent = null
                }
            )
        }

        // [추가] 대표 사진 변경 팝업 (그리드 형태)
        if (isPhotoPickerOpen) {
            PhotoSelectionDialog(
                photoUrls = allMonthPhotoUrls,
                onPhotoSelected = { newUrl ->
                    currentMainPhoto = newUrl // 사진 변경
                    isPhotoPickerOpen = false

                    onMainPhotoChanged(newUrl)
                },
                onDismiss = { isPhotoPickerOpen = false }
            )
        }
    }
}

@Composable
fun BookCover(
    mainPhotoUrl: String,
    month: String,
    onEditClick: () -> Unit,
    onFlipClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        // 👇 [수정] 카드 전체를 클릭하면 '뒤집기(onFlipClick)'가 실행됩니다.
        modifier = modifier.clickable { onFlipClick() },
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
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(Color.LightGray)
            ) {
                AsyncImage(
                    model = mainPhotoUrl,
                    contentDescription = "Main Photo",
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize()
                )

                // 편집 버튼 (이 버튼을 누르면 뒤집히지 않고 편집 기능만 실행됨)
                IconButton(
                    onClick = { onEditClick() },
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(8.dp)
                        .size(36.dp)
                        .background(Color.Black.copy(alpha = 0.5f), CircleShape)
                ) {
                    Icon(
                        imageVector = Icons.Default.Edit,
                        contentDescription = "표지 변경",
                        tint = Color.White,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(60.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(PrimaryBlue),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = month,
                    color = Color.White,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}

// [추가] 사진 선택 팝업 (그리드)
@Composable
fun BookInside(
    storyData: StoryBookData,
    onEventClick: (StoryEvent) -> Unit,
    onFlipClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        // 👇 1. 카드 빈 공간(여백 등)을 클릭하면 뒤집힘
        modifier = modifier.clickable { onFlipClick() },
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

            // 요약글 구성
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
                    // 👇 2. 여기가 핵심 수정 부분입니다!

                    // 파란 글씨(키워드)를 눌렀는지 확인
                    val clickedAnnotation = annotatedString.getStringAnnotations(tag = "EVENT",
                        start = offset, end = offset).firstOrNull()

                    if (clickedAnnotation != null) {
                        // (A) 키워드를 눌렀으면 -> 팝업 띄우기
                        storyData.events.find { it.keyword == clickedAnnotation.item }?.let { event ->
                            onEventClick(event)
                        }
                    } else {
                        // (B) 키워드가 아닌 일반 글씨를 눌렀으면 -> 책 뒤집기 실행!
                        onFlipClick()
                    }
                },
                // ClickableText가 가로로 꽉 차게 해서 터치 영역을 확실히 잡도록 함
                modifier = Modifier.fillMaxWidth()
            )

            // 글씨 아래 남는 공간도 클릭하면 뒤집히도록 투명 박스 추가
            Spacer(modifier = Modifier.weight(1f).fillMaxWidth().clickable { onFlipClick() })
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

@Composable
fun PhotoSelectionDialog(
    photoUrls: List<String>,
    onPhotoSelected: (String) -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Color.White,
        title = {
            Text(text = "표지 사진 선택", fontWeight = FontWeight.Bold, fontSize = 18.sp)
        },
        text = {
            // 사진이 많을 수 있으니 그리드(바둑판) 모양으로 보여줌
            LazyVerticalGrid(
                columns = GridCells.Fixed(3), // 한 줄에 3개씩
                verticalArrangement = Arrangement.spacedBy(4.dp),
                horizontalArrangement = Arrangement.spacedBy(4.dp),
                modifier = Modifier.heightIn(max = 400.dp)
            ) {
                // items import가 안 되어 있다면 빨간 줄이 뜰 수 있습니다.
                // import androidx.compose.foundation.lazy.grid.items 를 추가하세요.
                items(photoUrls) { url ->
                    AsyncImage(
                        model = url,
                        contentDescription = null,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier
                            .aspectRatio(1f) // 정사각형 비율
                            .clip(RoundedCornerShape(4.dp))
                            .clickable { onPhotoSelected(url) } // 클릭하면 선택된 사진 주소를 넘겨줌
                    )
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("취소", color = Color.Gray)
            }
        }
    )
}
