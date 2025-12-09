# app/schemas/user.py
import datetime
from pydantic import BaseModel, EmailStr

# 회원가입 및 로그인 시 입력받는 데이터 형식
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserLogin(UserBase):
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# 응답 데이터 형식 (민감한 비밀번호는 제외)
class UserResponse(UserBase):
    id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True