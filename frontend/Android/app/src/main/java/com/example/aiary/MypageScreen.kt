package com.example.aiary

import android.app.Activity
import android.app.DatePickerDialog
import android.content.Intent
import android.net.Uri
import android.provider.MediaStore
import android.widget.DatePicker
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.KeyboardArrowRight
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.aiary.data.UserSession
import java.util.Calendar
import androidx.lifecycle.viewmodel.compose.viewModel

private val White = Color(0xFFFFFFFF)

@Composable
fun MyPageScreen(
    onLogout: () -> Unit,
    viewModel: MypageViewModel = viewModel(),
    currentBabyName: String,
    currentBabyBirthDate: String,
    currentProfileUri: Uri?,
    onUpdateProfile: (String, String) -> Unit,
    onUpdateProfileImage: (Uri) -> Unit
) {
    var babyName by remember { mutableStateOf(currentBabyName) }
    var babyBirthDate by remember { mutableStateOf(currentBabyBirthDate) }
    var babyGender by remember { mutableStateOf("남아") }

    val context = LocalContext.current
    val scrollState = rememberScrollState()

    // 갤러리 앱을 직접 실행
    val imagePickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val uri = result.data?.data
            if (uri != null) {
                onUpdateProfileImage(uri)
            }
        }
    }

    val calendar = Calendar.getInstance()
    val datePickerDialog = DatePickerDialog(
        context,
        { _: DatePicker, year: Int, month: Int, dayOfMonth: Int ->
            val formattedMonth = String.format("%02d", month + 1)
            val formattedDay = String.format("%02d", dayOfMonth)
            babyBirthDate = "$year-$formattedMonth-$formattedDay"
        },
        2024, 0, 1
    )
    var showPasswordDialog by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundBeige)
            .padding(24.dp)
            .verticalScroll(scrollState),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text("마이페이지", fontSize = 24.sp, fontWeight = FontWeight.Bold, color = DarkGray, modifier = Modifier.padding(top = 16.dp, bottom = 32.dp))

        Card(
            colors = CardDefaults.cardColors(containerColor = White),
            elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) {

                // 프로필 사진 영역
                Box(
                    contentAlignment = Alignment.BottomEnd,
                    modifier = Modifier
                        .size(100.dp)
                        .clickable {
                            // 갤러리 앱(MediaStore)을 호출하는 Intent 실행
                            val intent = Intent(Intent.ACTION_PICK, MediaStore.Images.Media.EXTERNAL_CONTENT_URI)
                            imagePickerLauncher.launch(intent)
                        }
                ) {
                    if (currentProfileUri != null) {
                        AsyncImage(
                            model = currentProfileUri,
                            contentDescription = "프로필 사진",
                            contentScale = ContentScale.Crop,
                            modifier = Modifier
                                .fillMaxSize()
                                .clip(CircleShape)
                                .border(2.dp, PrimaryBlue, CircleShape)
                        )
                    } else {
                        Image(
                            painter = painterResource(id = R.drawable.baby_icon),
                            contentDescription = "기본 프로필",
                            contentScale = ContentScale.Crop,
                            modifier = Modifier
                                .fillMaxSize()
                                .clip(CircleShape)
                                .border(2.dp, PrimaryBlue, CircleShape)
                        )
                    }

                    Box(modifier = Modifier.size(30.dp).background(DarkGray, CircleShape).padding(6.dp)) {
                        Icon(Icons.Default.Edit, contentDescription = "수정", tint = White)
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))

                OutlinedTextField(
                    value = babyName, onValueChange = { babyName = it },
                    label = { Text("아이 이름(태명)") }, singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = PrimaryBlue, unfocusedBorderColor = Color.LightGray)
                )

                Spacer(modifier = Modifier.height(16.dp))

                OutlinedTextField(
                    value = babyBirthDate, onValueChange = {}, label = { Text("생년월일") },
                    readOnly = true,
                    trailingIcon = {
                        IconButton(onClick = { datePickerDialog.show() }) {
                            Icon(painterResource(android.R.drawable.ic_menu_my_calendar), contentDescription = "달력")
                        }
                    },
                    modifier = Modifier.fillMaxWidth().clickable { datePickerDialog.show() },
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = PrimaryBlue, unfocusedBorderColor = Color.LightGray)
                )

                Spacer(modifier = Modifier.height(16.dp))

                Row(modifier = Modifier.fillMaxWidth()) {
                    GenderButton("왕자님 👑", babyGender == "남아", { babyGender = "남아" },
                        Modifier.weight(1f))
                    Spacer(modifier = Modifier.width(8.dp))
                    GenderButton("공주님 🎀", babyGender == "여아", { babyGender = "여아" },
                        Modifier.weight(1f))
                }

                Spacer(modifier = Modifier.height(24.dp))

                Button(
                    onClick = {
                        onUpdateProfile(babyName, babyBirthDate)
                        Toast.makeText(context, "정보가 수정되었습니다!", Toast.LENGTH_SHORT).show()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = PrimaryBlue),
                    modifier = Modifier.fillMaxWidth().height(50.dp), shape = RoundedCornerShape(12.dp)
                ) {
                    Text("저장하기", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                }
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        Text("계정 설정", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = Color.Gray,
            modifier = Modifier.align(Alignment.Start).padding(bottom = 8.dp))
        Card(colors = CardDefaults.cardColors(containerColor = White), shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth()) {
            Column {
                SettingItem(title = "이메일 정보", value = UserSession.userEmail ?: "이메일 없음")
                HorizontalDivider(color = BackgroundBeige)
                SettingItem(title = "비밀번호 변경", isArrow = true, onClick = { showPasswordDialog = true })
                HorizontalDivider(color = BackgroundBeige)
                SettingItem(title = "로그아웃", isArrow = true, onClick = onLogout, textColor = Color.Red)
            }
        }
        Spacer(modifier = Modifier.height(50.dp))
    }

    if (showPasswordDialog){
        ChangePasswordDialog(onDismiss = { showPasswordDialog = false }, onConfirm = {
            c, n -> viewModel.changePassword(context, c, n); showPasswordDialog = false })
    }
}


@Composable
fun GenderButton(
    text: String,
    isSelected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier.height(50.dp),
        shape = RoundedCornerShape(12.dp),
        border = if (isSelected) null else androidx.compose.foundation.BorderStroke(1.dp, Color.LightGray),
        colors = ButtonDefaults.outlinedButtonColors(
            containerColor = if (isSelected) PrimaryBlue.copy(alpha = 0.2f) else Color.Transparent,
            contentColor = if (isSelected) PrimaryBlue else Color.Gray
        )
    ) {
        Text(text, fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal)
    }
}

@Composable
fun SettingItem(
    title: String,
    value: String = "",
    isArrow: Boolean = false,
    textColor: Color = DarkGray,
    onClick: () -> Unit = {}
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(enabled = isArrow || onClick != {}) { onClick() }
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(text = title, fontSize = 16.sp, color = textColor)
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (value.isNotEmpty()) {
                Text(text = value, fontSize = 14.sp, color = Color.Gray)
            }
            if (isArrow) {
                Icon(Icons.Default.KeyboardArrowRight, contentDescription = null, tint = Color.Gray)
            }
        }
    }
}

@Composable
fun ChangePasswordDialog(
    onDismiss: () -> Unit,
    onConfirm: (String, String) -> Unit
) {
    var currentPassword by remember { mutableStateOf("") }
    var newPassword by remember { mutableStateOf("") }
    var confirmNewPassword by remember { mutableStateOf("") }
    var errorMessage by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Color.White,
        title = { Text(text = "비밀번호 변경", fontWeight = FontWeight.Bold, fontSize = 18.sp) },
        text = {
            Column {
                OutlinedTextField(
                    value = currentPassword,
                    onValueChange = { currentPassword = it },
                    label = { Text("현재 비밀번호") },
                    singleLine = true,
                    visualTransformation = androidx.compose.ui.text.input.PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value = newPassword,
                    onValueChange = { newPassword = it },
                    label = { Text("새 비밀번호 (6자리 이상)") },
                    singleLine = true,
                    visualTransformation = androidx.compose.ui.text.input.PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value = confirmNewPassword,
                    onValueChange = { confirmNewPassword = it },
                    label = { Text("새 비밀번호 확인") },
                    singleLine = true,
                    visualTransformation = androidx.compose.ui.text.input.PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth()
                )
                if (errorMessage.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(text = errorMessage, color = Color.Red, fontSize = 12.sp)
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (currentPassword.isEmpty() || newPassword.isEmpty()) {
                        errorMessage = "모든 항목을 입력해주세요."
                    } else if (newPassword.length < 6) {
                        errorMessage = "새 비밀번호는 6자리 이상이어야 합니다."
                    } else if (newPassword != confirmNewPassword) {
                        errorMessage = "새 비밀번호가 일치하지 않습니다."
                    } else {
                        onConfirm(currentPassword, newPassword)
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = PrimaryBlue),
                shape = RoundedCornerShape(8.dp)
            ) {
                Text("변경")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("취소", color = Color.Gray) }
        },
        shape = RoundedCornerShape(16.dp)
    )
}
