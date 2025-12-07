package com.example.aiary

import androidx.compose.animation.Crossfade
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.wrapContentHeight
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
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch

private val White = Color(0xFFFFFFFF)


data class DiaryPhoto(
    val imageRes: Int,
    val comment: String // 한 줄 코멘트
)

// 줄글 일기를 담을 데이터 (나중에는 Map에서 가져올 내용)
data class DiaryEntryData(
    val photos: List<DiaryPhoto>,
    val fullDiaryText: String // 전체 일기 (줄글)
)

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun CardDiaryScreen(
    selectedDate: String, // 날짜를 받아옴
    onBack: () -> Unit    // 뒤로 가기 기능
) {
    // 앞/뒷면 상태 관리 변수 (false: 앞면, true: 뒷면)
    var isFlipped by remember { mutableStateOf(false) }

    // 임시 데이터 (실제 프로젝트에서는 Map[selectedDate]에서 DiaryEntryData를 가져와야 합니다)
    val entryData = remember(selectedDate) {
        DiaryEntryData(
            photos = listOf(
                DiaryPhoto(R.drawable.baby_icon, "오늘 아침, 맘마 먹고 기분 좋은 @@! 🍼"),
                DiaryPhoto(R.drawable.baby_icon, "낮잠 자는 천사 같은 모습 💤"),
                DiaryPhoto(R.drawable.baby_icon, "@@이가 새로운 장난감이 마음에 드나 봐요 🧸")
            ),
            fullDiaryText = """
                2025년 12월 25일 크리스마스🎄. 
                오늘은 @@이가 태어나서 맞는 두 번째 크리스마스였다. 아침에 일어나자마자 머리맡에 놓인 양말 속 장난감을 발견하고 소리를 지르는데, 그 모습이 얼마나 귀여운지! 

                오후에는 거실에서 아빠랑 새로 받은 곰 인형을 가지고 한참을 놀았다. 곰 인형의 코를 만지면서 옹알이를 하는데, 새로운 단어를 배우는 것 같아서 신기했다. 내년 크리스마스에는 걸어 다니면서 같이 캐럴을 부를 수 있겠지? 사랑한다 우리 아가.
            """.trimIndent()
        )
    }

    // Pager 및 Coroutine Scope 설정
    val diaryPhotos = entryData.photos
    val fullDiaryText = entryData.fullDiaryText
    val pagerState = rememberPagerState(pageCount = { diaryPhotos.size })
    val coroutineScope = rememberCoroutineScope()


    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundBeige)
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 24.dp),
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
                // Crossfade: 자연스러운 전환 효과
                Crossfade(targetState = isFlipped, label = "FlipAnimation") { flipped ->
                    if (!flipped) {
                        // 앞면 (사진 + 한 줄 코멘트)
                        FrontSideContent(
                            diaryPhotos = diaryPhotos,
                            pagerState = pagerState,
                            coroutineScope = coroutineScope
                        )
                    } else {
                        // 뒷면 (전체 일기 텍스트)
                        BackSideContent(fullDiaryText = fullDiaryText)
                    }
                }
            }
            // 뒷면일 때 페이지 인디케이터를 숨김
            if (!isFlipped) {
                Spacer(modifier = Modifier.height(10.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center
                ) {
                    // 현재 페이지 표시
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

//  앞면 UI Composable 분리
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
                Image(
                    painter = painterResource(id = diaryPhotos[page].imageRes),
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize()
                )
            }

            // 좌우 화살표 로직
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

// 뒷면 UI Composable 분리
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
        // 스크롤 가능
        Text(
            text = fullDiaryText,
            fontSize = 15.sp,
            color = DarkGray,
            modifier = Modifier.verticalScroll(rememberScrollState())
        )
    }
}