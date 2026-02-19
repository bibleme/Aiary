package com.example.aiary

import android.os.Build
import android.util.Log
import androidx.annotation.RequiresApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.time.YearMonth
import com.example.aiary.data.UserSession
import com.example.aiary.network.RetrofitClient

@RequiresApi(Build.VERSION_CODES.O)
@Composable
fun CalendarScreen(onDateClick: (String) -> Unit) {
    // 현재 보여줄 '연도'와 '월'을 상태로 관리
    var currentYearMonth by remember { mutableStateOf(YearMonth.now()) }

    // [추가 1] 일기가 작성된 날짜(일)들을 저장하는 Set (예: 5일, 12일에 썼다면 setOf(5, 12))
    var writtenDays by remember { mutableStateOf<Set<Int>>(emptySet()) }

    // [추가 2] 달(currentYearMonth)이 바뀔 때마다 서버에서 일기 목록을 확인합니다.
    LaunchedEffect(currentYearMonth) {
        try {
            val myId = UserSession.userId
            val response = RetrofitClient.api.getDiaries(myId)

            if (response.isSuccessful) {
                val allDiaries = response.body() ?: emptyList()

                // 현재 보고 있는 달을 "YYYY-MM" 형식으로 만듭니다 (예: "2025-12")
                val targetPrefix = String.format("%04d-%02d", currentYearMonth.year, currentYearMonth.monthValue)

                // 이번 달에 해당하는 일기들의 '일(day)'만 뽑아내서 중복 제거(toSet)
                val daysWithDiary = allDiaries.mapNotNull { diary ->
                    val dateStr = diary.diary_date ?: diary.created_at
                    // 날짜 형태가 "2025-12-11T..." 라고 가정하고 앞부분이 일치하는지 확인
                    if (dateStr.startsWith(targetPrefix) && dateStr.length >= 10) {
                        // 8번째부터 10번째 앞까지 자르면 "11" 같은 일(day)이 나옴
                        dateStr.substring(8, 10).toIntOrNull()
                    } else {
                        null
                    }
                }.toSet()

                writtenDays = daysWithDiary // 상태 업데이트 -> 화면이 다시 그려짐
            }
        } catch (e: Exception) {
            Log.e("CalendarScreen", "일기 목록 불러오기 실패", e)
        }
    }

    val daysInMonth = currentYearMonth.lengthOfMonth()
    val firstDayOfWeek = currentYearMonth.atDay(1).dayOfWeek.value % 7
    val weekDays = listOf("일", "월", "화", "수", "목", "금", "토")

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundBeige)
            .padding(24.dp)
    ) {
        // 상단 헤더
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 24.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            IconButton(onClick = { currentYearMonth = currentYearMonth.minusMonths(1) }) {
                Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, contentDescription = "이전 달", tint = DarkGray)
            }
            Text(
                text = "${currentYearMonth.year}년 ${currentYearMonth.monthValue}월",
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = DarkGray
            )
            IconButton(onClick = { currentYearMonth = currentYearMonth.plusMonths(1) }) {
                Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = "다음 달", tint = DarkGray)
            }
        }

        // 요일 헤더
        Row(modifier = Modifier.fillMaxWidth()) {
            weekDays.forEach { day ->
                Text(
                    text = day,
                    modifier = Modifier.weight(1f),
                    textAlign = TextAlign.Center,
                    color = if (day == "일") Color.Red else DarkGray,
                    fontWeight = FontWeight.Bold
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // 날짜 그리드
        LazyVerticalGrid(
            columns = GridCells.Fixed(7),
            modifier = Modifier.fillMaxSize()
        ) {
            // 앞쪽 빈 칸 채우기
            items(firstDayOfWeek) {
                Box(modifier = Modifier.size(40.dp))
            }

            // 날짜 채우기
            items(daysInMonth) { index ->
                val day = index + 1
                Box(
                    modifier = Modifier
                        .padding(4.dp)
                        .aspectRatio(1f)
                        .clip(RoundedCornerShape(12.dp))
                        .background(Color.White)
                        .clickable {
                            onDateClick("${currentYearMonth.year}년 ${currentYearMonth.monthValue}월 ${day}일")
                        }
                ) {
                    // 글씨 (정중앙 배치)
                    Text(
                        text = day.toString(),
                        fontSize = 16.sp,
                        color = DarkGray,
                        fontWeight = FontWeight.Medium,
                        modifier = Modifier.align(Alignment.Center)
                    )

                    // 만약 이 날짜(day)에 일기가 쓰여 있다면 우측 상단에 빨간 점 표시!
                    if (writtenDays.contains(day)) {
                        Box(
                            modifier = Modifier
                                .align(Alignment.TopEnd) 
                                .padding(8.dp) 
                                .size(6.dp) 
                                .background(Color.Red, CircleShape) // 빨간색 동그라미
                        )
                    }
                }
            }
        }
    }
}

@RequiresApi(Build.VERSION_CODES.O)
@Preview(showBackground = true)
@Composable
fun CalendarScreenPreview() {
    CalendarScreen(onDateClick = {})
}
