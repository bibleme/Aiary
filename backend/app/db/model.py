# backend/app/db/model.py
import datetime
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # ✅ 재로그인 강제(기존 토큰 무효화)용
    token_version = Column(Integer, nullable=False, default=0)

    diaries = relationship(
        "Diary",
        back_populates="owner",
        cascade="all, delete-orphan",
    )


class Diary(Base):
    __tablename__ = "diaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    content = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    # ✅ 프론트가 보내는 일기 날짜(YYYY-MM-DD)
    diary_date = Column(Date, nullable=False, default=datetime.date.today, index=True)

    owner = relationship("User", back_populates="diaries")
