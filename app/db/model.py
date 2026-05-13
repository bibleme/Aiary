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
    token_version = Column(Integer, nullable=False, default=0)

    diaries = relationship(
        "Diary",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    daily_diaries = relationship(
        "DailyDiary",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    monthly_reports = relationship(
        "MonthlyReport",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    vision_images = relationship(
        "VisionImage",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Diary(Base):
    __tablename__ = "one_line_diaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    image_url = Column(String, nullable=False)
    image_storage = Column(String(20), nullable=False, default="local")
    image_key = Column(Text, nullable=True)
    image_filename = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    diary_date = Column(Date, nullable=False, default=datetime.date.today, index=True)

    owner = relationship("User", back_populates="diaries")
    vision_image = relationship(
        "VisionImage",
        back_populates="diary",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class DailyDiary(Base):
    __tablename__ = "daily_diaries"
    __table_args__ = (
        UniqueConstraint("user_id", "diary_date", name="uq_daily_diaries_user_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    diary_date = Column(Date, nullable=False, index=True)

    content = Column(Text, nullable=True)
    generated_content = Column(Text, nullable=True)
    edited_content = Column(Text, nullable=True)
    model_version = Column(String, nullable=True)
    generation_meta = Column(JSON, nullable=True)
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


class MonthlyReport(Base):
    __tablename__ = "monthly_reports"
    __table_args__ = (
        UniqueConstraint("user_id", "target_month", name="uq_monthly_reports_user_month"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_month = Column(String(7), nullable=False, index=True)
    report_json = Column(JSON, nullable=False)

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


class VisionImage(Base):
    __tablename__ = "vision_images"
    __table_args__ = (
        UniqueConstraint("one_line_diary_id", name="uq_vision_images_diary"),
    )

    id = Column(Integer, primary_key=True, index=True)
    one_line_diary_id = Column(
        Integer,
        ForeignKey("one_line_diaries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    file_name = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    year_month = Column(String(7), nullable=False, index=True)
    
    image_storage = Column(String(20), nullable=False, default="local")
    image_key = Column(Text, nullable=True)
    image_filename = Column(String, nullable=True)

    basic_cv_status = Column(String(20), nullable=False, default="pending", index=True)
    face_cv_status = Column(String(20), nullable=False, default="pending", index=True)
    basic_cv_attempts = Column(Integer, nullable=False, default=0)
    face_cv_attempts = Column(Integer, nullable=False, default=0)
    locked_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    cv_status = Column(String(20), nullable=False, default="pending", index=True)
    error_message = Column(Text, nullable=True)

    predicted_tag = Column(String, nullable=True)
    scene_vector = Column(JSON, nullable=True)

    target_child_found = Column(Boolean, nullable=False, default=False)
    target_child_confidence = Column(Float, nullable=True)

    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )

    owner = relationship("User", back_populates="vision_images")
    diary = relationship("Diary", back_populates="vision_image")

    persons = relationship(
        "VisionPerson",
        back_populates="vision_image",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    object_instances = relationship(
        "VisionObjectInstance",
        back_populates="vision_image",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="VisionObjectInstance.vision_image_id",
    )

    appearances = relationship(
        "VisionAppearance",
        back_populates="vision_image",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    interactions = relationship(
        "VisionInteraction",
        back_populates="vision_image",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class VisionPerson(Base):
    __tablename__ = "vision_persons"

    id = Column(Integer, primary_key=True, index=True)
    vision_image_id = Column(
        Integer,
        ForeignKey("vision_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role = Column(String, nullable=False)
    emotion = Column(String, nullable=True)
    emotion_score = Column(Float, nullable=True)
    bbox = Column(JSON, nullable=True)
    face_confidence = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    vision_image = relationship("VisionImage", back_populates="persons")


class VisionObjectInstance(Base):
    __tablename__ = "vision_object_instances"

    id = Column(Integer, primary_key=True, index=True)

    vision_image_id = Column(
        Integer,
        ForeignKey("vision_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    base_category = Column(String, nullable=False, index=True)
    feature_vector = Column(JSON, nullable=True)
    parent_assigned_name = Column(String, nullable=True)

    first_seen_vision_image_id = Column(
        Integer,
        ForeignKey("vision_images.id"),
        nullable=True,
    )

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    vision_image = relationship(
        "VisionImage",
        back_populates="object_instances",
        foreign_keys=[vision_image_id],
    )

    first_seen_vision_image = relationship(
        "VisionImage",
        foreign_keys=[first_seen_vision_image_id],
    )


class VisionAppearance(Base):
    __tablename__ = "vision_appearances"

    id = Column(Integer, primary_key=True, index=True)
    vision_image_id = Column(
        Integer,
        ForeignKey("vision_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    entity_type = Column(String, nullable=False)  # person / object
    entity_id = Column(Integer, nullable=False)
    bbox = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    vision_image = relationship("VisionImage", back_populates="appearances")


class VisionInteraction(Base):
    __tablename__ = "vision_interactions"

    id = Column(Integer, primary_key=True, index=True)
    vision_image_id = Column(
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
    object_instance_id = Column(
        Integer,
        ForeignKey("vision_object_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    interaction_type = Column(String, nullable=True)
    proximity_score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    vision_image = relationship("VisionImage", back_populates="interactions")