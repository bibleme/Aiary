# app/api/endpoints/user.py
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete

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
    result = await db.execute(select(User).where(User.email == user.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    new_user = User(
        email=user.email,
        hashed_password=get_password_hash(user.password),
        token_version=0,  # ✅ 명시(선택)
    )
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

    # ✅ token_version 포함 (재로그인 강제 기반)
    access_token = create_access_token(
        data={"sub": str(user.id), "token_version": int(user.token_version)},
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
    # 1) 기존 비밀번호 확인
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="기존 비밀번호가 일치하지 않습니다.")

    # 2) 새 비밀번호 동일 여부 체크
    if payload.old_password == payload.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="새 비밀번호는 기존 비밀번호와 달라야 합니다.")

    # 3) 변경 저장 + ✅ 기존 토큰 즉시 무효화
    current_user.hashed_password = get_password_hash(payload.new_password)
    current_user.token_version = int(current_user.token_version) + 1

    await db.commit()
    await db.refresh(current_user)

    return {
        "message": "비밀번호가 변경되었습니다. 보안을 위해 다시 로그인해주세요.",
        "relogin_required": True,
        "error_code": "RELOGIN_REQUIRED",
    }


# -------------------- 4. 회원탈퇴 (본인 계정 삭제) --------------------
@router.delete("/me", status_code=status.HTTP_200_OK)
async def delete_me(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    ✅ 회원탈퇴:
    - 본인 일기 먼저 삭제(외래키 충돌 방지)
    - 그 다음 본인 계정 삭제
    """
    # 1) diaries 먼저 삭제 (FK 충돌 방지)
    await db.execute(sa_delete(Diary).where(Diary.user_id == current_user.id))

    # 2) user 삭제
    await db.execute(sa_delete(User).where(User.id == current_user.id))

    await db.commit()

    return {
        "message": "회원탈퇴가 완료되었습니다.",
        "relogin_required": True,
        "error_code": "ACCOUNT_DELETED",
    }
