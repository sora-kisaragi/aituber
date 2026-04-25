"""システム設定の参照・更新 API を提供する。"""

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
    "tts_speaker_excited": "スタイル excited 用の話者名（空ならデフォルト話者）",
    "tts_speaker_neutral": "スタイル neutral 用の話者名（空ならデフォルト話者）",
    "tts_speaker_calm": "スタイル calm 用の話者名（空ならデフォルト話者）",
    "llm_api_base": "LLM API ベース URL（OpenAI 互換）",
    "llm_api_key": "LLM API キー",
    "llm_model_name": "実況生成に使う LLM モデル名",
    "vlm_model_name": "フレーム解析に使う VLM モデル名",
    "segment_duration": "動画分割のセグメント長（秒）",
    "event_grouping_window": "イベント集約ウィンドウ（秒）",
    "game_audio_volume": "ゲーム音量比率（0.0〜1.0、実況音声に対する元動画音量）",
    "planner_min_silence_seconds": "発話間に必ず空ける最小無言時間（秒）",
    "planner_plan_duration_seconds": "発話計画の基準長（秒）",
    "planner_speak_threshold": "この重要度未満は発話しない（0.0〜1.0）",
    "planner_max_talk_ratio": "直近ウィンドウ内で許可する最大発話率（0.0〜1.0）",
    "planner_talk_window_seconds": "発話率計算に使う時間窓（秒）",
    "planner_max_queue_delay_seconds": "イベント発生から遅延許容する最大秒数（秒）",
    "compose_overlap_min_gap_seconds": "合成時に発話同士へ追加する最小間隔（秒）",
    "compose_overlap_strategy": "重複時の解消戦略（shift / clip_previous）",
    "compose_clip_min_keep_seconds": "clip_previous 時に残す最小発話長（秒未満は破棄）",
}

# Web UI から変更を許可するキー（database_url・media_root 等はサーバー管理）
_EDITABLE_KEYS: set[str] = {
    "tts_base_url",
    "tts_default_mode",
    "tts_default_speaker",
    "tts_default_language",
    "tts_default_instruct",
    "tts_speaker_excited",
    "tts_speaker_neutral",
    "tts_speaker_calm",
    "llm_api_base",
    "llm_api_key",
    "llm_model_name",
    "vlm_model_name",
    "segment_duration",
    "event_grouping_window",
    "game_audio_volume",
    "planner_min_silence_seconds",
    "planner_plan_duration_seconds",
    "planner_speak_threshold",
    "planner_max_talk_ratio",
    "planner_talk_window_seconds",
    "planner_max_queue_delay_seconds",
    "compose_overlap_min_gap_seconds",
    "compose_overlap_strategy",
    "compose_clip_min_keep_seconds",
}


@router.get("/", response_model=list[SystemSettingRead])
def get_settings(db: Session = Depends(get_db)) -> list[SystemSettingRead]:
    """現在の設定一覧を返す。

    Args:
        db: DB セッション。

    Returns:
        UI で編集可能な設定の一覧。DB 値がない場合は `.env` の既定値を返す。
    """
    db_map = {r.key: r.value for r in db.query(SystemSetting).all()}
    env_dict = settings.model_dump()

    result = []
    for key in _EDITABLE_KEYS:
        value = db_map.get(key, str(env_dict.get(key, "")))
        result.append(
            SystemSettingRead(
                key=key,
                value=value,
                description=_DESCRIPTIONS.get(key),
            )
        )
    return sorted(result, key=lambda x: x.key)


@router.put("/", response_model=list[SystemSettingRead])
def update_settings(
    updates: list[SystemSettingUpdate],
    db: Session = Depends(get_db),
) -> list[SystemSettingRead]:
    """設定を DB に保存する。

    Args:
        updates: 更新対象の設定キーと値。
        db: DB セッション。

    Returns:
        更新後の設定一覧。
    """
    for item in updates:
        if item.key not in _EDITABLE_KEYS:
            continue
        row = db.query(SystemSetting).filter(SystemSetting.key == item.key).first()
        if row:
            row.value = item.value
            row.updated_at = datetime.utcnow()
        else:
            db.add(
                SystemSetting(
                    key=item.key,
                    value=item.value,
                    description=_DESCRIPTIONS.get(item.key),
                )
            )
    db.commit()
    return get_settings(db)
