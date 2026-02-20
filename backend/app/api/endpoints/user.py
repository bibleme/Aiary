# app/api/endpoints/user.py

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.config import settings
from app.db.database import get_db_session
from app.db.model import User, Diary
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token, PasswordChangeRequest
from app.services.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/users", tags=["users"])


# -------------------- 1. 회원가입 --------------------
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db_session)):
    # 이메일 중복 확인
    result = await db.execute(select(User).where(User.email == user.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # 비밀번호 해시 + 저장
    new_user = User(email=user.email, hashed_password=get_password_hash(user.password))
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


# -------------------- 2. 로그인 --------------------
@router.post("/login", response_model=Token)
async def login_user(user_data: UserLogin, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


# -------------------- 3. 비밀번호 변경 --------------------
@router.put("/password", status_code=status.HTTP_200_OK)
async def change_password(
    payload: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Authorization: Bearer <access_token> 헤더가 있어야 동작함
    """
    # 1) 기존 비밀번호 확인
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="기존 비밀번호가 일치하지 않습니다.")

    # 2) 새 비밀번호 동일 여부 체크
    if payload.old_password == payload.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="새 비밀번호는 기존 비밀번호와 달라야 합니다.")

    # 3) 변경 저장
    current_user.hashed_password = get_password_hash(payload.new_password)
    await db.commit()
    await db.refresh(current_user)

    return {"message": "비밀번호가 성공적으로 변경되었습니다."}

# -------------------- 4. 회원 탈퇴 (Withdraw / Delete Account) --------------------
@router.delete("/withdraw", status_code=status.HTTP_200_OK)
async def withdraw_user(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user) # 토큰으로 본인(현재 로그인한 유저) 확인
):
    """
    토큰 인증 기반 회원 탈퇴 API
    - 유저가 작성한 모든 일기(Diary)를 먼저 삭제한 뒤, 계정을 삭제합니다.
    """
    try:
        # 1. 해당 유저가 작성한 모든 일기 데이터 일괄 삭제
        # 데이터베이스에 "Diary 테이블에서 user_id가 이 사람인 거 다 지워!" 라고 명령
        await db.execute(
            delete(Diary).where(Diary.user_id == current_user.id)
        )
        
        # 2. 유저(User) 계정 데이터 삭제
        await db.delete(current_user)
        
        # 3. 변경사항 최종 승인 (데이터베이스에 완전히 반영)
        await db.commit()
        
        return {"message": "회원 탈퇴가 완료되었습니다."}
        
    except Exception as e:
        # 중간에 하나라도 에러가 나면 지우던 것을 멈추고 원래대로 되돌림(롤백)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"회원 탈퇴 처리 중 오류가 발생했습니다: {str(e)}"
        )
