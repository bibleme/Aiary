package com.example.aiary

import android.os.Build
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


@RequiresApi(Build.VERSION_CODES.O)
@Composable
fun CalendarScreen(onDateClick: (String) -> Unit) {
    // 현재 보여줄 '연도'와 '월'을 상태로 관리 (초기값: 오늘 날짜)
    var currentYearMonth by remember { mutableStateOf(YearMonth.now()) }

    // 그 달이 며칠까지 있는지 계산
    val daysInMonth = currentYearMonth.lengthOfMonth()

    // 3. 그 달의 1일이 무슨 요일인지 계산 (1:월, 2:화, ... 7:일)
    // 달력은 보통 '일요일'부터 시작하므로, 일요일을 0으로 맞추기 위해 % 7 연산을 합니다.
    // (결과: 일=0, 월=1, 화=2, ... 토=6)
    val firstDayOfWeek = currentYearMonth.atDay(1).dayOfWeek.value % 7

    val weekDays = listOf("일", "월", "화", "수", "목", "금", "토")

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundBeige) // 프로젝트에 정의된 색상
            .padding(24.dp)
    ) {
        // 상단 헤더 (이전달 <  2026년 1월  > 다음달)
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 24.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            // [이전 달 버튼]
            IconButton(onClick = { currentYearMonth = currentYearMonth.minusMonths(1) }) {
                Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, contentDescription = "이전 달", tint = DarkGray)
            }

            // [현재 연월 표시]
            Text(
                text = "${currentYearMonth.year}년 ${currentYearMonth.monthValue}월",
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = DarkGray
            )

            // [다음 달 버튼]
            IconButton(onClick = { currentYearMonth = currentYearMonth.plusMonths(1) }) {
                Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = "다음 달", tint = DarkGray)
            }
        }

        // 요일 헤더 (일 월 화 수 목 금 토)
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
            // 달력 앞쪽의 빈 칸 채우기 (1일이 시작하기 전까지)
            items(firstDayOfWeek) {
                Box(modifier = Modifier.size(40.dp))
            }

            // 1일부터 말일까지 날짜 채우기
            items(daysInMonth) { index ->
                val day = index + 1 // index는 0부터 시작하므로 1을 더해줌
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier
                        .padding(4.dp)
                        .aspectRatio(1f)
                        .clip(RoundedCornerShape(12.dp))
                        .background(Color.White)
                        .clickable {
                            // 클릭 시: "2026년 1월 15일" 형태로 전달
                            onDateClick("${currentYearMonth.year}년 ${currentYearMonth.monthValue}월 ${day}일")
                        }
                ) {
                    Text(
                        text = day.toString(),
                        fontSize = 16.sp,
                        color = DarkGray,
                        fontWeight = FontWeight.Medium
                    )
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
