# app/db/model.py
import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # 비밀번호 변경 후 기존 토큰 무효화용
    token_version = Column(Integer, nullable=False, default=0)

    diaries = relationship(
        "Diary",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # 하루일기 테이블 추가
    daily_diaries = relationship(
        "DailyDiary",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Diary(Base):
    __tablename__ = "diaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)
    image_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)

    # 한줄일기 생성 날짜 저장
    diary_date = Column(Date, nullable=False, default=datetime.date.today, index=True)

    owner = relationship("User", back_populates="diaries")


class DailyDiary(Base):
    __tablename__ = "daily_diaries"
    __table_args__ = (
        # 유저별 같은 날짜 하루일기 1개만 허용
        UniqueConstraint("user_id", "diary_date", name="uq_daily_diaries_user_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    diary_date = Column(Date, nullable=False, index=True)
    content = Column(Text, nullable=False)

    # 하루일기 생성 시 사용한 한줄일기 개수
    source_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )

    owner = relationship("User", back_populates="daily_diaries")
