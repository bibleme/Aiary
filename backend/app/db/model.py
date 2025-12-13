# app/db/models.py (이 파일이 Base 객체를 정의합니다)

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base # 🚨 Base 정의를 여기로 옮깁니다.

import datetime

Base = declarative_base() # 👈 이 프로젝트의 모든 모델은 여기서 정의된 Base를 상속받습니다.

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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    content = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    owner = relationship("User", back_populates="diaries")