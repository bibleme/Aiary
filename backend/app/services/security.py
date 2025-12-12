# app/services/security.py

from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security, HTTPException, status
from sqlalchemy.future import select
from typing import Optional
from app.config import settings
from app.db.database import get_db_session
from app.db.model import User

# -------------------- Hashing Context --------------------
# bcrypt 스키마를 명시하여 UnknownHashError를 해결합니다.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """평문 비밀번호와 해시된 비밀번호를 비교합니다."""
    # passlib.context.verify 함수는 정상적인 bcrypt 해시 포맷을 요구합니다.
    print(f"\n[DEBUG_AUTH] Received Pass: '{plain_password}' | Stored Hash: {hashed_password}\n")
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """비밀번호를 해시하여 저장합니다."""
    return pwd_context.hash(password)

# -------------------- JWT Generation --------------------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    
    # 토큰 만료 시간 설정
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # settings에서 ACCESS_TOKEN_EXPIRE_MINUTES를 사용 (일관성 유지)
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # JWT 생성: settings.SECRET_KEY 사용 (인코딩)
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt

# -------------------- JWT Verification --------------------

def decode_access_token(token: str):
    """토큰을 복호화하여 payload를 반환합니다. 실패 시 None."""
    try:
        # 🚨 수정: 반드시 settings.SECRET_KEY를 사용해야 합니다! (디코딩)
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None

# [참고] FastAPI 의존성 함수: 토큰을 검증하고 현재 사용자 객체를 반환합니다.
# 이 함수는 users.py 등에서 @Depends(get_current_user) 형태로 사용됩니다.
security = HTTPBearer()

async def get_current_user(
    token: HTTPAuthorizationCredentials = Security(security),
    db: Optional[get_db_session] = None # 여기서 get_db_session을 사용하도록 수정 필요
) -> User:
    # 1. 토큰 디코딩
    payload = decode_access_token(token.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. User ID 추출
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. DB에서 사용자 조회
    if db is None:
        raise HTTPException(status_code=500, detail="Database session not available")
    
    result = await db.execute(select(User).filter(User.id == int(user_id)))
    user = result.scalars().first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user