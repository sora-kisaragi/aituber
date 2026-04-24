from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class VideoCreate(BaseModel):
    title: str


class VideoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    duration_seconds: float | None
    fps: float | None
    storage_path: str
    video_metadata: dict[str, Any]
    created_at: datetime | None


class VideoUpdate(BaseModel):
    title: str | None = None
    tags: list[str] | None = None
    tags_manual: list[str] | None = None


class VideoTagRead(BaseModel):
    tags_manual: list[str]
    tags_auto_rule: list[str]
    tags_auto_llm: list[str]
    tags_suggested_llm: list[str]
    tags_effective: list[str]
    source_by_tag: dict[str, str]
    tag_status: dict[str, str | None]


class SegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    video_id: uuid.UUID
    start_time: float
    end_time: float
    segment_type: str
    storage_path: str | None


class FrameRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    segment_id: uuid.UUID
    timestamp: float
    image_path: str | None
    features: dict[str, Any]


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    segment_id: uuid.UUID
    timestamp: float
    event_type: str
    importance: float
    details: dict[str, Any]


class UtterancePlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    video_id: uuid.UUID
    event_ids: list[str]
    start_time: float
    end_time: float
    priority: int
    style: str


class CommentaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    utterance_plan_id: uuid.UUID
    language: str
    style: str
    text: str


class AudioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    commentary_id: uuid.UUID
    tts_mode: str
    speaker: str
    language: str
    storage_path: str | None
    duration_seconds: float | None


class SubtitleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    commentary_id: uuid.UUID
    file_path: str | None
    start_time: float
    end_time: float


class TimelineItem(BaseModel):
    start_time: float
    end_time: float
    style: str
    text: str
    commentary_id: str
    audio_rel: str | None


class VideoTimeline(BaseModel):
    input_rel: str | None
    items: list[TimelineItem]


class SystemSettingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: str
    description: str | None


class SystemSettingUpdate(BaseModel):
    key: str
    value: str


class TTSSynthesizeRequest(BaseModel):
    text: str
    mode: str = "custom_voice"
    speaker: str = "ono_anna"
    language: str = "japanese"
    instruct: str = ""
    output_path: str = ""
