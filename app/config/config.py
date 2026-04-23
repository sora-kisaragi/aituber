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
                base[k] = field_type(v)
    return Settings.model_validate(base)
