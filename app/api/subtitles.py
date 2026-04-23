from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Subtitle
from app.models.schemas import SubtitleRead

router = APIRouter()


@router.get("/", response_model=list[SubtitleRead])
def list_subtitles(commentary_id: str = "", db: Session = Depends(get_db)) -> list[Subtitle]:
    q = db.query(Subtitle)
    if commentary_id:
        q = q.filter(Subtitle.commentary_id == commentary_id)
    return q.order_by(Subtitle.start_time).all()


@router.get("/{subtitle_id}", response_model=SubtitleRead)
def get_subtitle(subtitle_id: str, db: Session = Depends(get_db)) -> Subtitle:
    subtitle = db.query(Subtitle).filter(Subtitle.id == subtitle_id).first()
    if not subtitle:
        raise HTTPException(status_code=404, detail="字幕が見つかりません")
    return subtitle
