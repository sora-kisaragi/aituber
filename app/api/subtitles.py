"""字幕（Subtitle）参照 API。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.subtitle import SubtitleService
from app.db.session import get_db
from app.models.models import Subtitle
from app.models.schemas import SubtitleRead

router = APIRouter()


@router.get("/", response_model=list[SubtitleRead])
def list_subtitles(commentary_id: str = "", db: Session = Depends(get_db)) -> list[Subtitle]:
    """字幕一覧を返す。

    Args:
        commentary_id: 指定時は該当実況文IDに紐づく字幕のみ返す。
        db: DB セッション。

    Returns:
        開始時刻順の字幕配列。
    """
    q = db.query(Subtitle)
    if commentary_id:
        q = q.filter(Subtitle.commentary_id == commentary_id)
    return q.order_by(Subtitle.start_time).all()


@router.get("/{subtitle_id}", response_model=SubtitleRead)
def get_subtitle(subtitle_id: str, db: Session = Depends(get_db)) -> Subtitle:
    """字幕IDを指定して1件取得する。

    Args:
        subtitle_id: 字幕ID。
        db: DB セッション。

    Returns:
        該当する字幕。
    """
    subtitle = db.query(Subtitle).filter(Subtitle.id == subtitle_id).first()
    if not subtitle:
        raise HTTPException(status_code=404, detail="字幕が見つかりません")
    return subtitle


@router.get("/{subtitle_id}/webvtt", response_class=PlainTextResponse)
def get_subtitle_webvtt(subtitle_id: str, db: Session = Depends(get_db)) -> PlainTextResponse:
    """SRT 字幕を WebVTT 形式に変換して返す（video タグの <track> 用）。

    Args:
        subtitle_id: 変換対象字幕ID。
        db: DB セッション。

    Returns:
        `text/vtt` 形式のレスポンス。
    """
    subtitle = db.query(Subtitle).filter(Subtitle.id == subtitle_id).first()
    if not subtitle:
        raise HTTPException(status_code=404, detail="字幕が見つかりません")
    if not subtitle.file_path or not Path(subtitle.file_path).exists():
        raise HTTPException(status_code=404, detail="字幕ファイルが見つかりません")

    srt_content = Path(subtitle.file_path).read_text(encoding="utf-8")
    vtt_content = SubtitleService.to_webvtt(srt_content)
    return PlainTextResponse(content=vtt_content, media_type="text/vtt")
