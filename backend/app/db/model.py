# app/db/model.py
import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Date,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

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
    __tablename__ = "one_line_diaries"

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


# -------------------------------------------------------------------
# 👁️ Vision AI 분석 상세 테이블 (5개)
# -------------------------------------------------------------------

class VisionImage(Base):
    """원본 코드의 ImageDB 역할 + Diary 테이블과 연결"""
    __tablename__ = 'vision_images'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 어떤 한 줄 일기(사진)에 대한 분석인지 연결
    diary_id = Column(Integer, ForeignKey('one_line_diaries.id', ondelete="CASCADE"), nullable=False, unique=True)
    
    file_name = Column(String, nullable=False)
    predicted_scene = Column(String)  # Indoor / Outdoor
    
    # 🌟 추가됨: 리포트의 장소 클러스터링을 위한 CLIP 임베딩 벡터 저장 (JSON 텍스트)
    scene_vector = Column(Text, nullable=True) 
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계 설정 (Diary 쪽에도 vision_image = relationship(...) 추가 필요)
    diary = relationship("Diary", backref="vision_image")
    appearances = relationship("VisionAppearance", back_populates="image", cascade="all, delete-orphan")
    interactions = relationship("VisionInteraction", back_populates="image", cascade="all, delete-orphan")
    object_instances = relationship("VisionObjectInstance", back_populates="first_seen_image")


class VisionPerson(Base):
    """원본 코드의 Person 역할"""
    __tablename__ = 'vision_persons'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String, nullable=False)  # Target_Child, Adult_Helper 등
    emotion = Column(String)               # happy, sad 등
    
    # 🌟 추가됨: 리포트의 베스트 컷(신뢰도 높은 사진) 추출을 위한 감정 확률 점수
    emotion_score = Column(Float, nullable=True) 

    interactions = relationship("VisionInteraction", back_populates="person", cascade="all, delete-orphan")


class VisionObjectInstance(Base):
    """원본 코드의 ObjectInstance 역할 (SigLIP 사물 기억용)"""
    __tablename__ = 'vision_object_instances'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    feature_vector = Column(Text)  # JSON String으로 변환된 SigLIP 임베딩 벡터
    base_category = Column(String, nullable=False) # YOLO가 찾은 이름 (예: teddy bear)
    parent_assigned_name = Column(String, nullable=True) # 부모가 나중에 지어줄 이름
    first_seen_image_id = Column(Integer, ForeignKey('vision_images.id', ondelete="SET NULL"))

    first_seen_image = relationship("VisionImage", back_populates="object_instances")
    interactions = relationship("VisionInteraction", back_populates="object_instance", cascade="all, delete-orphan")


class VisionAppearance(Base):
    """원본 코드의 Appearance 역할 (바운딩 박스 위치 정보)"""
    __tablename__ = 'vision_appearances'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey('vision_images.id', ondelete="CASCADE"))
    entity_type = Column(String, nullable=False) # 'Person' 또는 'Object'
    entity_id = Column(Integer, nullable=False)  # Person ID 또는 ObjectInstance ID
    bounding_box = Column(Text)                  # JSON String 형태의 박스 좌표

    image = relationship("VisionImage", back_populates="appearances")


class VisionInteraction(Base):
    """원본 코드의 Interaction 역할 (사람과 사물의 상호작용)"""
    __tablename__ = 'vision_interactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey('vision_images.id', ondelete="CASCADE"))
    person_id = Column(Integer, ForeignKey('vision_persons.id', ondelete="CASCADE"))
    instance_id = Column(Integer, ForeignKey('vision_object_instances.id', ondelete="CASCADE"))
    
    interaction_type = Column(String)     # Hand_Holding 등
    proximity_score = Column(Float)       # 근접도 점수

    image = relationship("VisionImage", back_populates="interactions")
    person = relationship("VisionPerson", back_populates="interactions")
    object_instance = relationship("VisionObjectInstance", back_populates="interactions")