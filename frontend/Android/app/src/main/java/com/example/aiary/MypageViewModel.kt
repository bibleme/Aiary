package com.example.aiary

import android.content.Context
import android.widget.Toast
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.aiary.data.ChangePasswordRequest
import com.example.aiary.data.UserSession
import com.example.aiary.network.RetrofitClient
import kotlinx.coroutines.launch

class MypageViewModel : ViewModel() {

    // 비밀번호 변경 함수
    fun changePassword(context: Context, currentPw: String, newPw: String) {
        viewModelScope.launch {
            try {
                // UserSession에서 토큰을 꺼내 "Bearer " 형식으로 만듭니다.
                val token = "Bearer ${UserSession.accessToken}"

                val request = ChangePasswordRequest(
                    old_password = currentPw,
                    new_password = newPw
                )

                // API를 호출할 때 토큰(token)과 데이터(request)를 함께 보냅니다!
                val response = RetrofitClient.api.changePassword(token, request)

                if (response.isSuccessful) {
                    Toast.makeText(context, "비밀번호가 성공적으로 변경되었습니다.", Toast.LENGTH_SHORT).show()
                } else {
                    // 백엔드 가이드라인에 맞춰 에러 원인을 더 정확히 알려줍니다.
                    val errorMessage = when(response.code()) {
                        400 -> "현재 비밀번호가 틀렸거나, 새 비밀번호가 기존과 같습니다."
                        401 -> "로그인이 풀렸습니다. 다시 로그인해주세요."
                        422 -> "입력 형식이 잘못되었습니다."
                        else -> "변경 실패: ${response.code()}"
                    }
                    Toast.makeText(context, errorMessage, Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                Toast.makeText(context, "네트워크 오류 발생: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    // 회원 탈퇴 함수
    fun deleteAccount(context: Context, onNavigateToLogin: () -> Unit) {
        viewModelScope.launch {
            try {
                // 1. 토큰 꺼내기
                val token = "Bearer ${UserSession.accessToken}"

                // 2. 백엔드에 탈퇴 요청 보내기
                val response = RetrofitClient.api.deleteAccount(token)

                if (response.isSuccessful) {
                    Toast.makeText(context, "회원탈퇴가 완료되었습니다. 그동안 감사했습니다! 😭", Toast.LENGTH_SHORT).show()

                    // 3. 내 폰에 저장된 정보(세션) 싹 비우기
                    UserSession.accessToken = ""
                    UserSession.userEmail = ""

                    // 4. 로그인 화면으로 강제 이동시키기
                    onNavigateToLogin()
                } else {
                    Toast.makeText(context, "탈퇴 실패: 서버 오류(${response.code()})", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(context, "네트워크 오류 발생: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
