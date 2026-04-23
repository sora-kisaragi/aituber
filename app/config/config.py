from pydantic_settings import BaseSettings


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
    log_level: str = "INFO"

    segment_duration: int = 5
    event_grouping_window: int = 3

    model_config = {"env_file": ".env"}


settings = Settings()
