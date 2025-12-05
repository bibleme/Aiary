package com.example.aiary_login

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun ImageUploadScreen(onBack: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFFDF5E6))
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // 상단
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 16.dp, bottom = 40.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // 뒤로가기 버튼
            IconButton(onClick = { onBack() }) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = "뒤로 가기",
                    tint = Color.Black
                )
            }

            Spacer(modifier = Modifier.width(8.dp))

            Text(
                text = "사진 업로드",
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = Color.Black
            )
        }

        // 사진 업로드 영역
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(300.dp)
                .background(Color.White, shape = RoundedCornerShape(16.dp))
                .clickable {
                    // Todo: 갤러리에서 사진 받아오기
                },
            contentAlignment = Alignment.Center
        ) {
            val stroke = Stroke(width = 5f, pathEffect = PathEffect.dashPathEffect(floatArrayOf(20f, 20f), 0f))
            Canvas(modifier = Modifier.fillMaxSize()) {
                drawRoundRect(color = Color(0xFFa7c5eb), style = stroke, cornerRadius = androidx.compose.ui.geometry.CornerRadius(16.dp.toPx()))
            }

            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(text = "+", fontSize = 50.sp, color = Color(0xFFa7c5eb))
                Text(text = "사진을 선택하거나 드래그하세요", color = Color(0xFF888888), fontSize = 14.sp)
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        Text(
            text = "최대 10장까지 선택 가능합니다.\n아이의 표정이 잘 보이는 사진이 좋아요!",
            color = Color(0xFF888888),
            fontSize = 12.sp,
            textAlign = androidx.compose.ui.text.style.TextAlign.Center
        )

        Spacer(modifier = Modifier.weight(1f))

        Button(
            onClick = { /* TODO: 이미지 분석 */ },
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFa7c5eb)),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth().height(56.dp)
        ) {
            Text("AI 분석 시작", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = Color.White)
        }
    }
}

@Preview(showBackground = true)
@Composable
fun ImageUploadScreenPreview() {
    ImageUploadScreen(onBack = {})
}