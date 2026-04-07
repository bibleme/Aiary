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
    JSON,
    Float,
    Boolean,
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
    
    # 월별 리포트 테이블
    monthly_reports = relationship(
        "MonthlyReport",
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

    # 기존 컬럼: 바로 삭제하지 않고 호환용으로 잠시 유지
    content = Column(Text, nullable=True)

    # 새 구조
    generated_content = Column(Text, nullable=True)
    edited_content = Column(Text, nullable=True)

    model_version = Column(String, nullable=True)
    generation_meta = Column(JSON, nullable=True)

    # 하루일기 생성 시 사용한 한줄일기 개수
    source_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )
    edited_at = Column(DateTime(timezone=True), nullable=True)
    
    owner = relationship("User", back_populates="daily_diaries")
    
    
class VisionImage(Base):
    __tablename__ = "vision_images"

    id = Column(Integer, primary_key=True, index=True)
    diary_id = Column(
        Integer,
        ForeignKey("one_line_diaries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name = Column(String, nullable=False)
    predicted_scene = Column(String, nullable=True)  # Indoor / Outdoor
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    diary = relationship("Diary")
    persons = relationship(
        "VisionPerson",
        back_populates="image",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    appearances = relationship(
        "VisionAppearance",
        back_populates="image",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    interactions = relationship(
        "VisionInteraction",
        back_populates="image",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class VisionPerson(Base):
    __tablename__ = "vision_persons"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(
        Integer,
        ForeignKey("vision_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Target_Child / Adult_Helper / Assumed_Child
    role = Column(String, nullable=False, index=True)
    emotion = Column(String, nullable=True)

    # reference child match score 등 저장용
    similarity_score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    image = relationship("VisionImage", back_populates="persons")


class VisionObjectInstance(Base):
    __tablename__ = "vision_object_instances"

    id = Column(Integer, primary_key=True, index=True)

    # "teddy bear", "bottle" 같은 base category
    base_category = Column(String, nullable=False, index=True)

    # 나중에 사람이 이름 붙일 수 있는 칸
    parent_assigned_name = Column(String, nullable=True)

    # siglip 임베딩은 일단 JSON/text로 저장하는 것보다
    # 지금은 nullable text로 두고 추후 pgvector 전환 추천
    feature_vector = Column(Text, nullable=True)

    first_seen_image_id = Column(
        Integer,
        ForeignKey("vision_images.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    appearances = relationship(
        "VisionAppearance",
        back_populates="object_instance",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class VisionAppearance(Base):
    __tablename__ = "vision_appearances"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(
        Integer,
        ForeignKey("vision_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Person / Object
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)

    # JSON string "[x1, y1, x2, y2]" 저장
    bounding_box = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    image = relationship("VisionImage", back_populates="appearances")
    object_instance = relationship(
        "VisionObjectInstance",
        primaryjoin="foreign(VisionAppearance.entity_id)==VisionObjectInstance.id",
        back_populates="appearances",
        viewonly=True,
    )


class VisionInteraction(Base):
    __tablename__ = "vision_interactions"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(
        Integer,
        ForeignKey("vision_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    person_id = Column(
        Integer,
        ForeignKey("vision_persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    instance_id = Column(
        Integer,
        ForeignKey("vision_object_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    interaction_type = Column(String, nullable=False, index=True)  # Hand_Holding 등
    proximity_score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    image = relationship("VisionImage", back_populates="interactions")
    
    
class MonthlyReport(Base):
    __tablename__ = "monthly_reports"
    __table_args__ = (
        UniqueConstraint("user_id", "target_month", name="uq_monthly_reports_user_month"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 예: "2026-03"
    target_month = Column(String(7), nullable=False, index=True)

    # 최종 리포트 전체 JSON
    report_json = Column(JSON, nullable=False)

    # 최신 여부 판단용
    source_diary_count = Column(Integer, nullable=False, default=0)
    source_hash = Column(String(64), nullable=False, default="")
    generation_version = Column(String, nullable=True)

    last_source_created_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )

    owner = relationship("User", back_populates="monthly_reports")