package com.example.aiary.data

// 특정 행동 이벤트 (예: 배밀이, 앉기)
data class StoryEvent(
    val keyword: String, // "배밀이", "앉기", "놀이"
    val photoUrls: List<String>, // 관련 사진 URL 리스트
    val description: String // 팝업 제목 (예: "아이의 배밀이 사진")
)

// 월간 스토리북 전체 데이터
data class StoryBookData(
    val month: String, // "2025.02"
    val mainPhotoUrl: String, // 메인 사진 URL
    val summary: String, // 전체 요약글 (여기에 키워드가 포함됨)
    val events: List<StoryEvent> // 요약글에 포함된 이벤트 목록
)
