from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.clients.qwen_tts_client import QwenTTSClient
from app.config.config import get_runtime_settings, settings
from app.db.session import get_db
from app.models.schemas import TTSSynthesizeRequest
from sqlalchemy.orm import Session

router = APIRouter()


def _tts_client(db: Session) -> QwenTTSClient:
    cfg = get_runtime_settings(db)
    return QwenTTSClient(base_url=cfg.tts_base_url)


@router.get("/speakers")
def get_speakers(db: Session = Depends(get_db)) -> dict:
    """custom_voice モードで使える話者一覧を TTS サーバーから取得して返す。"""
    return {"speakers": _tts_client(db).list_speakers()}


@router.get("/profiles")
def get_profiles(db: Session = Depends(get_db)) -> dict:
    """保存済みプロファイル一覧を TTS サーバーから取得して返す。"""
    return {"profiles": _tts_client(db).list_profiles()}


@router.get("/languages")
def get_languages(db: Session = Depends(get_db)) -> dict:
    """対応言語一覧を TTS サーバーから取得して返す。"""
    return {"languages": _tts_client(db).list_languages()}


@router.post("/synthesize")
def synthesize(body: TTSSynthesizeRequest) -> dict:
    """テキストを音声合成して WAV ファイルを保存し、パスと音声長を返す。"""
    if not body.output_path:
        raise HTTPException(status_code=422, detail="output_path は必須です")

    client = QwenTTSClient(
        base_url=settings.tts_base_url,
        default_mode=settings.tts_default_mode,
        default_speaker=settings.tts_default_speaker,
        default_language=settings.tts_default_language,
        default_instruct=settings.tts_default_instruct,
    )
    duration = client.synthesize(
        text=body.text,
        output_path=body.output_path,
        mode=body.mode,
        speaker=body.speaker,
        language=body.language,
        instruct=body.instruct,
    )
    return {"output_path": body.output_path, "duration_seconds": duration}
