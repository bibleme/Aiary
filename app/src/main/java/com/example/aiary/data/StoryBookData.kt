package com.example.aiary.data

// 특정 행동 이벤트 
data class StoryEvent(
    val keyword: String, 
    val photoUrls: List<String>, 
    val description: String
)

data class StoryBookData(
    val month: String, 
    val mainPhotoUrl: String, 
    val summary: String, 
    val events: List<StoryEvent> 
)
