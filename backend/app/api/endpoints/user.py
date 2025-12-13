# app/api/endpoints/user.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta
from app.config import settings

from app.db.database import get_db_session
from app.db.model import User
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token
from app.services.security import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/users", tags=["users"])

# -------------------- 1. 회원가입 (Registration) --------------------
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db_session)):
    # 1. 이메일 중복 확인 
    result = await db.execute(select(User).filter(User.email == user.email))
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # 2. 비밀번호 해시
    hashed_password = get_password_hash(user.password)
    
    # 3. 사용자 객체 생성 및 저장
    new_user = User(email=user.email, hashed_password=hashed_password)
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user

# -------------------- 2. 로그인 (Login / Authentication) --------------------
@router.post("/login", response_model=Token) 
async def login_user(user_data: UserLogin, db: AsyncSession = Depends(get_db_session)):
    # 1. 사용자 조회 및 비밀번호 검증 (기존 로직 유지)
    result = await db.execute(select(User).filter(User.email == user_data.email))
    user = result.scalars().first()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # 2. [추가된 로직] JWT Access Token 생성
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        # 토큰에 sub(Subject)라는 이름으로 user ID를 담습니다.
        data={"sub": str(user.id)}, 
        expires_delta=access_token_expires
    )
    
    # 3. 토큰 반환
    return {"access_token": access_token, "token_type": "bearer"}