package com.example.aiary

import android.os.Build
import androidx.annotation.RequiresApi
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.aiary.data.StoryBookData
import java.util.Collections.checkedList 

val BookInsideBg = Color(0xFFF0F0F0)
val KeywordBlue = Color(0xFF4A90E2)

@RequiresApi(Build.VERSION_CODES.O)
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BookStoryScreen(
    storyData: StoryBookData,
    allMonthPhotoUrls: List<String>,
    onBack: () -> Unit
) {
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
        },
        containerColor = BackgroundBeige // 화면 배경색 Scaffold에 설정
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp),
            contentAlignment = Alignment.Center
        ) {
            BookInside(
                storyData = storyData,
                photoUrls = allMonthPhotoUrls, // 임시로 띄워줄 전체 사진 리스트를 넘겨줍니다.
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(0.7f) // 책 모양 비율 유지
            )
        }
    }
}

@Composable
fun BookInside(
    storyData: StoryBookData,
    photoUrls: List<String>,
    modifier: Modifier = Modifier
) {

    val dummyPhotos = if (photoUrls.size >= 3) {
        photoUrls.take(3)
    } else {
        photoUrls
    }

    Card(
        modifier = modifier, // Just use the passed modifier (clickable 제거)
        shape = RoundedCornerShape(16.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp),
        colors = CardDefaults.cardColors(containerColor = BookInsideBg)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp)
                // 내용이 길어지면 위아래로 스크롤 가능하게 만듦
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.Start
        ) {
            // 상단 타이틀 (월)
            Text(
                text = storyData.month,
                fontSize = 24.sp,
                fontWeight = FontWeight.ExtraBold,
                color = DarkGray,
                modifier = Modifier.padding(bottom = 20.dp)
            )

            // 🎁 1. 이 달의 물건
            CategoryPhotoRow(
                title = "🧸 이 달의 물건!",
                photos = dummyPhotos
            )

            Spacer(modifier = Modifier.height(24.dp))

            // 😊 2. 이 달의 감정
            CategoryPhotoRow(
                title = "😊 이 달의 감정!",
                photos = dummyPhotos
            )

            Spacer(modifier = Modifier.height(24.dp))

            // 🏕️ 3. 이 달의 장소
            CategoryPhotoRow(
                title = "🏕️ 이 달의 장소!",
                photos = dummyPhotos
            )

            // 하단 빈 공간 ( removeclickable spacer)
            Spacer(modifier = Modifier.weight(1f).fillMaxWidth().height(40.dp))
        }
    }
}

// 👇 각 카테고리별 제목과 사진 가로 스크롤을 만들어주는 공통 UI 컴포넌트
@Composable
fun CategoryPhotoRow(
    title: String,
    photos: List<String>
) {
    Column {
        // 카테고리 제목
        Text(
            text = title,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            color = KeywordBlue,
            modifier = Modifier.padding(bottom = 8.dp)
        )

        // 사진 가로 리스트
        if (photos.isNotEmpty()) {
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                items(photos) { url ->
                    AsyncImage(
                        model = url,
                        contentDescription = "Category Photo",
                        contentScale = ContentScale.Crop,
                        modifier = Modifier
                            .size(90.dp) // 사진 크기를 90x90 정사각형으로 고정
                            .clip(RoundedCornerShape(12.dp))
                            .background(Color.LightGray)
                    )
                }
            }
        } else {
            // 사진이 아예 없을 때 보여줄 안내 문구
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(90.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(Color.LightGray.copy(alpha = 0.5f)),
                contentAlignment = Alignment.Center
            ) {
                Text(text = "아직 사진이 없어요 텅~", color = Color.Gray, fontSize = 14.sp)
            }
        }
    }
}
