package com.example.aiary_login

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp


@Composable
fun CalendarScreen(onDateClick: (String) -> Unit) {
    // 2025년 12월 달력 데이터
    val days = (1..31).toList()
    val weekDays = listOf("일", "월", "화", "수", "목", "금", "토")
    val emptyDays = 1

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundBeige)
            .padding(24.dp)
    ) {
        // 상단 제목
        Text(
            text = "2025년 12월",
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            color = DarkGray,
            modifier = Modifier
                .padding(vertical = 24.dp)
                .align(Alignment.CenterHorizontally)
        )

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
            // 앞쪽 빈 날짜 채우기
            items(emptyDays) {
                Box(modifier = Modifier.size(40.dp))
            }

            // 1일부터 31일까지 날짜 채우기
            items(days.size) { index ->
                val day = days[index]
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier
                        .padding(4.dp)
                        .aspectRatio(1f)
                        .background(Color.White, RoundedCornerShape(12.dp))
                        .clickable {
                            // 날짜 클릭 시 해당 날짜를 들고 이동
                            onDateClick("2025년 12월 ${day}일")
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

@Preview(showBackground = true)
@Composable
fun CalendarScreenPreview() {
    CalendarScreen(onDateClick = {})
}