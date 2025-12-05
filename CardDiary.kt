package com.example.aiary_login

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch


data class DiaryPhoto(
    val imageRes: Int,
    val comment: String
)

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun CardDiaryScreen(
    selectedDate: String, // 날짜를 받아옴
    onBack: () -> Unit    // 뒤로 가기 기능
) {
    val diaryData = listOf(
        DiaryPhoto(R.drawable.baby_icon, "오늘 아침, 맘마 먹고 기분 좋은 @@! 🍼"),
        DiaryPhoto(R.drawable.baby_icon, "낮잠 자는 천사 같은 모습 💤"),
        DiaryPhoto(R.drawable.baby_icon, "@@이가 새로운 장난감이 마음에 드나 봐요 🧸")
    )
    val pagerState = rememberPagerState(pageCount = { diaryData.size })
    val coroutineScope = rememberCoroutineScope()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundBeige)
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // 1. 상단 네비게이션 (뒤로 가기 + 날짜)
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
                text = selectedDate, // 받아온 날짜 표시
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = DarkGray,
                modifier = Modifier.weight(1f),
                textAlign = TextAlign.Center
            )
            // 균형을 맞추기 위한 투명 아이콘
            Spacer(modifier = Modifier.size(48.dp))
        }

        // 카드형 다이어리
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.Center
        ) {
            Card(
                colors = CardDefaults.cardColors(containerColor = Color.White),
                elevation = CardDefaults.cardElevation(defaultElevation = 8.dp),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth().wrapContentHeight()
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.padding(16.dp)
                ) {
                    Box(modifier = Modifier.fillMaxWidth().height(300.dp).clip(RoundedCornerShape(12.dp))) {
                        HorizontalPager(state = pagerState) { page ->
                            Image(
                                painter = painterResource(id = diaryData[page].imageRes),
                                contentDescription = null,
                                contentScale = ContentScale.Crop,
                                modifier = Modifier.fillMaxSize()
                            )
                        }
                        if (pagerState.currentPage > 0) {
                            IconButton(
                                onClick = { coroutineScope.launch { pagerState.animateScrollToPage(pagerState.currentPage - 1) } },
                                modifier = Modifier.align(Alignment.CenterStart).padding(8.dp).background(Color.White.copy(0.7f), CircleShape)
                            ) { Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, null, tint = DarkGray) }
                        }
                        if (pagerState.currentPage < diaryData.size - 1) {
                            IconButton(
                                onClick = { coroutineScope.launch { pagerState.animateScrollToPage(pagerState.currentPage + 1) } },
                                modifier = Modifier.align(Alignment.CenterEnd).padding(8.dp).background(Color.White.copy(0.7f), CircleShape)
                            ) { Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, null, tint = DarkGray) }
                        }
                    }
                    Spacer(modifier = Modifier.height(20.dp))
                    Text(
                        text = diaryData[pagerState.currentPage].comment,
                        fontSize = 16.sp,
                        color = DarkGray,
                        textAlign = TextAlign.Center,
                        fontWeight = FontWeight.Medium
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                }
            }
        }
    }
}