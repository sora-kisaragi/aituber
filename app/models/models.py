import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Video(Base):
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    duration_seconds = Column(Float)
    fps = Column(Float)
    storage_path = Column(Text, nullable=False)
    video_metadata = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    segments = relationship("Segment", back_populates="video", cascade="all, delete-orphan")
    utterance_plans = relationship(
        "UtterancePlan", back_populates="video", cascade="all, delete-orphan"
    )


class Segment(Base):
    __tablename__ = "segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    segment_type = Column("type", Text, default="gameplay")
    storage_path = Column(Text)

    video = relationship("Video", back_populates="segments")
    frames = relationship("Frame", back_populates="segment", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="segment", cascade="all, delete-orphan")


class Frame(Base):
    __tablename__ = "frames"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    segment_id = Column(
        UUID(as_uuid=True), ForeignKey("segments.id", ondelete="CASCADE"), nullable=False
    )
    timestamp = Column(Float, nullable=False)
    image_path = Column(Text)
    features = Column(JSONB, default=dict)

    segment = relationship("Segment", back_populates="frames")


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    segment_id = Column(
        UUID(as_uuid=True), ForeignKey("segments.id", ondelete="CASCADE"), nullable=False
    )
    timestamp = Column(Float, nullable=False)
    event_type = Column("type", Text, default="scene_change")
    importance = Column(Float, default=0.5)
    details = Column(JSONB, default=dict)

    segment = relationship("Segment", back_populates="events")


class UtterancePlan(Base):
    __tablename__ = "utterance_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    event_ids = Column(JSONB, default=list)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    priority = Column(Integer, default=1)
    style = Column(Text, default="calm")

    video = relationship("Video", back_populates="utterance_plans")
    commentaries = relationship(
        "Commentary", back_populates="utterance_plan", cascade="all, delete-orphan"
    )


class Commentary(Base):
    __tablename__ = "commentaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    utterance_plan_id = Column(
        UUID(as_uuid=True), ForeignKey("utterance_plans.id", ondelete="CASCADE"), nullable=False
    )
    language = Column(Text, default="japanese")
    style = Column(Text, default="calm")
    text = Column(Text, nullable=False)
    llm_raw_response = Column(JSONB, default=dict)

    utterance_plan = relationship("UtterancePlan", back_populates="commentaries")
    audios = relationship("Audio", back_populates="commentary", cascade="all, delete-orphan")
    subtitles = relationship("Subtitle", back_populates="commentary", cascade="all, delete-orphan")


class Audio(Base):
    __tablename__ = "audios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commentary_id = Column(
        UUID(as_uuid=True), ForeignKey("commentaries.id", ondelete="CASCADE"), nullable=False
    )
    tts_mode = Column(Text, default="custom_voice")
    speaker = Column(Text, default="ono_anna")
    language = Column(Text, default="japanese")
    storage_path = Column(Text)
    duration_seconds = Column(Float)

    commentary = relationship("Commentary", back_populates="audios")


class Subtitle(Base):
    __tablename__ = "subtitles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commentary_id = Column(
        UUID(as_uuid=True), ForeignKey("commentaries.id", ondelete="CASCADE"), nullable=False
    )
    file_path = Column(Text)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)

    commentary = relationship("Commentary", back_populates="subtitles")
