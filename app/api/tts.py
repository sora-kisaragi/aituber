from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.clients.qwen_tts_client import QwenTTSClient
from app.config.config import settings
from app.models.schemas import TTSSynthesizeRequest

router = APIRouter()


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
