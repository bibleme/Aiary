# backend/app/db/model.py
# (이 파일이 Base 객체를 정의합니다)

import datetime
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """회원가입 및 로그인에 사용되는 사용자 테이블"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    diaries = relationship("Diary", back_populates="owner")


class Diary(Base):
    """AI 육아일기 내용을 저장하는 테이블"""
    __tablename__ = "diaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    content = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    # ✅ 추가: 프론트가 보내는 "일기 날짜"
    # - DB에 컬럼이 없으면 반드시 마이그레이션 필요(아래 단계 참고)
    # - default는 callable로 줘야 해서 datetime.date.today (괄호 X)
    diary_date = Column(Date, nullable=False, default=datetime.date.today, index=True)

    owner = relationship("User", back_populates="diaries")
