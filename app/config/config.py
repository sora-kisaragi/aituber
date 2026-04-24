from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from pydantic_settings import BaseSettings

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class Settings(BaseSettings):
    database_url: str = "postgresql://localhost/aituber"

    tts_base_url: str = "http://localhost:7865"
    tts_default_mode: str = "custom_voice"
    tts_default_speaker: str = "ono_anna"
    tts_default_language: str = "japanese"
    tts_default_instruct: str = ""

    llm_api_base: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model_name: str = "gpt-4-turbo"
    vlm_model_name: str = "gemma3:27b"

    media_root: str = "/var/aituber/media"
    game_audio_volume: float = 0.3
    log_level: str = "INFO"

    segment_duration: int = 5
    event_grouping_window: int = 3
    planner_min_silence_seconds: float = 2.0
    planner_plan_duration_seconds: float = 3.0
    planner_speak_threshold: float = 0.3
    planner_max_talk_ratio: float = 0.5
    planner_talk_window_seconds: float = 60.0
    planner_max_queue_delay_seconds: float = 3.0
    compose_overlap_min_gap_seconds: float = 0.0

    model_config = {"env_file": ".env"}


settings = Settings()


def get_runtime_settings(db: Session) -> Settings:
    """DB の system_settings で .env 値を上書きした Settings を返す。"""
    from app.models.models import SystemSetting

    rows = db.query(SystemSetting).all()
    if not rows:
        return settings
    overrides = {r.key: r.value for r in rows}
    base = settings.model_dump()
    for k, v in overrides.items():
        if k in base:
            field_type = type(base[k])
            with contextlib.suppress(ValueError, TypeError):
                base[k] = field_type(v.strip() if isinstance(v, str) else v)
    return Settings.model_validate(base)
