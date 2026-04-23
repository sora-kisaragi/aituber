from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.config import settings
from app.db.session import get_db
from app.models.models import SystemSetting
from app.models.schemas import SystemSettingRead, SystemSettingUpdate

router = APIRouter()

# 設定キーの説明文（UI 表示用）
_DESCRIPTIONS: dict[str, str] = {
    "tts_base_url": "Qwen TTS サーバーの URL",
    "tts_default_mode": "TTS モード: voice_clone_profile / custom_voice / voice_design",
    "tts_default_speaker": "TTS デフォルト話者名（custom_voice 時）",
    "tts_default_language": "TTS 言語（auto / japanese / english）",
    "tts_default_instruct": "TTS スタイル指示文（空 = スタイルマップを使用）",
    "llm_api_base": "LLM API ベース URL（OpenAI 互換）",
    "llm_api_key": "LLM API キー",
    "llm_model_name": "実況生成に使う LLM モデル名",
    "vlm_model_name": "フレーム解析に使う VLM モデル名",
    "segment_duration": "動画分割のセグメント長（秒）",
    "event_grouping_window": "イベント集約ウィンドウ（秒）",
}

# Web UI から変更を許可するキー（database_url・media_root 等はサーバー管理）
_EDITABLE_KEYS: set[str] = {
    "tts_base_url", "tts_default_mode", "tts_default_speaker",
    "tts_default_language", "tts_default_instruct",
    "llm_api_base", "llm_api_key", "llm_model_name", "vlm_model_name",
    "segment_duration", "event_grouping_window",
}


@router.get("/", response_model=list[SystemSettingRead])
def get_settings(db: Session = Depends(get_db)) -> list[SystemSettingRead]:
    """現在の設定一覧を返す。DB 値がなければ .env のデフォルト値を返す。"""
    db_map = {r.key: r.value for r in db.query(SystemSetting).all()}
    env_dict = settings.model_dump()

    result = []
    for key in _EDITABLE_KEYS:
        value = db_map.get(key, str(env_dict.get(key, "")))
        result.append(SystemSettingRead(
            key=key,
            value=value,
            description=_DESCRIPTIONS.get(key),
        ))
    return sorted(result, key=lambda x: x.key)


@router.put("/", response_model=list[SystemSettingRead])
def update_settings(
    updates: list[SystemSettingUpdate],
    db: Session = Depends(get_db),
) -> list[SystemSettingRead]:
    """設定を DB に保存する。未知のキーは無視する。"""
    for item in updates:
        if item.key not in _EDITABLE_KEYS:
            continue
        row = db.query(SystemSetting).filter(SystemSetting.key == item.key).first()
        if row:
            row.value = item.value
            row.updated_at = datetime.utcnow()
        else:
            db.add(SystemSetting(
                key=item.key,
                value=item.value,
                description=_DESCRIPTIONS.get(item.key),
            ))
    db.commit()
    return get_settings(db)
