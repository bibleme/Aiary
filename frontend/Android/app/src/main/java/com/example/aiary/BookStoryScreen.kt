package com.example.aiary

import android.os.Build
import androidx.annotation.RequiresApi
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.ClickableText
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.aiary.data.KeywordAnnotation
import com.example.aiary.data.MonthlyReportResponse
import kotlin.math.absoluteValue
import androidx.compose.foundation.clickable
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import android.util.Log
import com.example.aiary.data.CVMonthlySummaryResponse
import androidx.compose.ui.res.painterResource

val BackgroundBlueGray = Color(0xFFF4F7FC)
val KeywordBlue = Color(0xFF4A90E2)
val CardBackground = Color.White
val TextDarkGray = Color(0xFF333333)

@RequiresApi(Build.VERSION_CODES.O)
@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
fun BookStoryScreen(
    reportData: MonthlyReportResponse,
    cvData: CVMonthlySummaryResponse,
    isUpToDate: Boolean = true,
    onRegenerate: () -> Unit = {},
    onBack: () -> Unit
) {
    var selectedKeywordAnn by remember { mutableStateOf<KeywordAnnotation?>(null) }
    val pagerState = rememberPagerState(pageCount = { 2 })

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("월간 리포트", fontWeight = FontWeight.Bold, color = TextDarkGray) },
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "뒤로", tint = TextDarkGray) }
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(containerColor = BackgroundBlueGray)
            )
        },
        containerColor = BackgroundBlueGray
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            if (!isUpToDate) {
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF9C4)),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 8.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp).fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text("새로운 기록이 있어요! 📝", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                            Text("새 한줄일기가 추가되어 리포트를 다시 만들 수 있어요.", fontSize = 12.sp, color = Color.DarkGray)
                        }
                        Button(
                            onClick = onRegenerate,
                            colors = ButtonDefaults.buttonColors(containerColor = KeywordBlue)
                        ) {
                            Text("업데이트 🔄", fontSize = 12.sp, color = Color.White)
                        }
                    }
                }
            }

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .padding(16.dp),
                contentAlignment = Alignment.Center
            ) {
                HorizontalPager(state = pagerState, modifier = Modifier.fillMaxSize()) { page ->
                    Box(
                        modifier = Modifier.fillMaxSize().graphicsLayer {
                            val pageOffset = (pagerState.currentPage - page) + pagerState.currentPageOffsetFraction
                            rotationY = pageOffset * 90f
                            alpha = if (pageOffset.absoluteValue >= 1f) 0f else 1f
                            transformOrigin = TransformOrigin(pivotFractionX = if (pageOffset < 0f) 1f else 0f, pivotFractionY = 0.5f)
                            cameraDistance = 12f * density
                        }
                    ) {
                        if (page == 0) {
                            TextReportPage(reportData = reportData, onKeywordClick = { ann -> selectedKeywordAnn = ann })
                        } else {
                            DataReportPage(cvData = cvData)
                        }
                    }
                }

                Row(modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 16.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    repeat(2) { index ->
                        Box(modifier = Modifier.size(8.dp).clip(RoundedCornerShape(50)).background(if (pagerState.currentPage == index) KeywordBlue else Color.LightGray))
                    }
                }
            }
        }

        if (selectedKeywordAnn != null) {
            KeywordPhotoDialog(
                keyword = selectedKeywordAnn!!.keyword,
                photoUrls = selectedKeywordAnn!!.photos.map { photoInfo ->
                    val url = photoInfo.full_image_url // (또는 photoInfo.image_url)

                    if (url.startsWith("http")) {
                        url // 이미 풀 주소면 그대로 사용
                    } else {
                        val baseUrl = "http://3.35.185.251:8000"
                        // 슬래시(/)가 겹치지 않게 안전하게 조립
                        if (url.startsWith("/")) {
                            "$baseUrl$url"
                        } else {
                            "$baseUrl/$url"
                        }
                    }
                },
                onDismiss = { selectedKeywordAnn = null }
            )
        }
    }
}

@Composable
fun TextReportPage(
    reportData: MonthlyReportResponse,
    onKeywordClick: (KeywordAnnotation) -> Unit
) {
    Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
        Box(modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(KeywordBlue.copy(alpha = 0.8f)).padding(20.dp)) {
            Column {
                Text("✨ 이달의 한 줄 요약", color = Color.White, fontSize = 14.sp)
                Spacer(modifier = Modifier.height(8.dp))
                Text(text = reportData.one_line_summary, color = Color.White, fontSize = 18.sp, lineHeight = 26.sp, fontWeight = FontWeight.Bold)
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        Card(
            shape = RoundedCornerShape(16.dp), colors = CardDefaults.cardColors(containerColor = CardBackground),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp), modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(24.dp)) {
                ReportSection("📅 이달의 모습", reportData.month_overview, reportData.keyword_annotations?.get("month_overview"), onKeywordClick)
                HorizontalDivider(modifier = Modifier.padding(vertical = 20.dp), color = Color(0xFFEEEEEE))

                ReportSection("📈 주요 활동 패턴", reportData.pattern_summary, reportData.keyword_annotations?.get("pattern_summary"), onKeywordClick)
                HorizontalDivider(modifier = Modifier.padding(vertical = 20.dp), color = Color(0xFFEEEEEE))

                ReportSection("✨ 새로운 변화", reportData.change_summary, reportData.keyword_annotations?.get("change_summary"), onKeywordClick)
                HorizontalDivider(modifier = Modifier.padding(vertical = 20.dp), color = Color(0xFFEEEEEE))

                ReportSection("💡 부모님께 드리는 말씀", reportData.parent_note, reportData.keyword_annotations?.get("parent_note"), onKeywordClick)
            }
        }
        Spacer(modifier = Modifier.height(40.dp))
    }
}

@Composable
fun ReportSection(title: String, fullText: String, annotations: List<KeywordAnnotation>?, onKeywordClick: (KeywordAnnotation) -> Unit) {
    Column {
        Text(text = title, fontWeight = FontWeight.Bold, fontSize = 16.sp, color = TextDarkGray)
        Spacer(modifier = Modifier.height(8.dp))

        val sortedAnnotations = annotations?.sortedBy { it.start } ?: emptyList()

        val annotatedString = buildAnnotatedString {
            var currentIndex = 0
            for (ann in sortedAnnotations) {
                if (ann.start >= currentIndex && ann.start < fullText.length) {
                    append(fullText.substring(currentIndex, ann.start))

                    val keywordText = fullText.substring(ann.start, minOf(ann.end, fullText.length))
                    pushStringAnnotation(tag = "KEYWORD", annotation = ann.keyword)
                    withStyle(SpanStyle(color = KeywordBlue, fontWeight = FontWeight.Bold, textDecoration = TextDecoration.Underline)) {
                        append(keywordText)
                    }
                    pop()
                    currentIndex = ann.end
                }
            }
            if (currentIndex < fullText.length) {
                append(fullText.substring(currentIndex))
            }
        }

        ClickableText(
            text = annotatedString,
            style = LocalTextStyle.current.copy(color = Color.DarkGray, fontSize = 15.sp, lineHeight = 24.sp),
            onClick = { offset ->
                annotatedString.getStringAnnotations("KEYWORD", offset, offset).firstOrNull()?.let { stringAnn ->
                    sortedAnnotations.find { it.keyword == stringAnn.item }?.let { onKeywordClick(it) }
                }
            }
        )
    }
}

// 📊 [화면 2] 데이터 리포트 (S3 URL 파싱 구조 반영)

@Composable
fun DataReportPage(cvData: CVMonthlySummaryResponse?) {
    if (cvData == null) return

    val objectPhotos = cvData.favorite_objects
        ?.flatMap { it.photo_items ?: emptyList() }
        ?.map { it.image_url }
        ?.distinct() ?: emptyList()

    val emotionPhotos = cvData.emotions_summary
        ?.mapNotNull { it.best_cut?.image_url }
        ?.distinct() ?: emptyList()

    val placePhotos = cvData.highlight_places
        ?.flatMap { it.photo_items ?: emptyList() }
        ?.map { it.image_url }
        ?.distinct() ?: emptyList()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        val displayMonth = cvData.report_month ?: "이번 달"

        Text(
            text = "📊 데이터로 보는 $displayMonth",
            fontSize = 20.sp,
            fontWeight = FontWeight.ExtraBold,
            color = TextDarkGray,
            modifier = Modifier.padding(bottom = 20.dp)
        )

        DataCard("📦 이달의 물건", objectPhotos)
        Spacer(modifier = Modifier.height(16.dp))

        DataCard("🏃 이달의 감정", emotionPhotos)
        Spacer(modifier = Modifier.height(16.dp))

        DataCard("🏕️ 이달의 장소", placePhotos)
        Spacer(modifier = Modifier.height(40.dp))
    }
}

@Composable
fun DataCard(title: String, photos: List<String>) {
    Card(shape = RoundedCornerShape(16.dp), colors = CardDefaults.cardColors(containerColor = CardBackground), elevation = CardDefaults.cardElevation(defaultElevation = 2.dp), modifier = Modifier.fillMaxWidth()) {
        Box(modifier = Modifier.padding(20.dp)) { CategoryPhotoRow(title = title, photos = photos) }
    }
}

@Composable
fun CategoryPhotoRow(title: String, photos: List<String>) {
    var selectedImageUrl by remember { mutableStateOf<String?>(null) }

    Column {
        Text(text = title, fontSize = 18.sp, fontWeight = FontWeight.Bold, color = TextDarkGray, modifier = Modifier.padding(bottom = 12.dp))
        if (photos.isNotEmpty()) {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
                items(photos) { url ->
                    AsyncImage(
                        model = url,
                        contentDescription = null, contentScale = ContentScale.Crop,
                        modifier = Modifier
                            .size(100.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .background(Color.LightGray)
                            .clickable { selectedImageUrl = url },
                        error = painterResource(id = android.R.drawable.ic_menu_report_image),
                        placeholder = painterResource(id = android.R.drawable.ic_menu_gallery)
                    )
                }
            }
        } else {
            Box(modifier = Modifier.fillMaxWidth().height(100.dp).clip(RoundedCornerShape(12.dp)).background(Color(0xFFF0F0F0)), contentAlignment = Alignment.Center) {
                Text(text = "사진이 부족해요 텅~", color = Color.Gray, fontSize = 14.sp)
            }
        }
    }

    selectedImageUrl?.let { url ->
        FullScreenImageDialog(
            imageUrl = url,
            onDismiss = { selectedImageUrl = null }
        )
    }
}

@Composable
fun KeywordPhotoDialog(keyword: String, photoUrls: List<String>, onDismiss: () -> Unit) {
    var selectedImageUrl by remember { mutableStateOf<String?>(null) }

    AlertDialog(
        onDismissRequest = onDismiss, containerColor = Color.White, shape = RoundedCornerShape(20.dp),
        title = {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text(text = "'$keyword' 사진", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                IconButton(onClick = onDismiss, modifier = Modifier.size(24.dp)) { Icon(Icons.Default.Close, contentDescription = "닫기") }
            }
        },
        text = {
            Column {
                Text(text = "${photoUrls.size}개의 순간", color = Color.Gray, fontSize = 14.sp, modifier = Modifier.padding(bottom = 16.dp))
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                    items(photoUrls) { url ->
                        AsyncImage(
                            model = url,
                            contentDescription = "Keyword Photo", contentScale = ContentScale.Crop,
                            modifier = Modifier
                                .size(120.dp)
                                .clip(RoundedCornerShape(12.dp))
                                .background(Color.LightGray)
                                .clickable { selectedImageUrl = url }
                        )
                    }
                }
            }
        },
        confirmButton = {}
    )

    selectedImageUrl?.let { url ->
        FullScreenImageDialog(
            imageUrl = url,
            onDismiss = { selectedImageUrl = null }
        )
    }
}

@Composable
fun FullScreenImageDialog(
    imageUrl: String,
    onDismiss: () -> Unit
) {
    Dialog(
        onDismissRequest = { onDismiss() },
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Black.copy(alpha = 0.9f))
                .clickable { onDismiss() }
        ) {
            AsyncImage(
                model = imageUrl,
                contentDescription = "확대된 사진",
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Fit
            )
            IconButton(
                onClick = { onDismiss() },
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(16.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Close,
                    contentDescription = "닫기",
                    tint = Color.White,
                    modifier = Modifier.size(32.dp)
                )
            }
        }
    }
}
