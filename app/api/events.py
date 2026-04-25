"""イベント（Event）参照 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Event
from app.models.schemas import EventRead

router = APIRouter()


@router.get("/", response_model=list[EventRead])
def list_events(segment_id: str = "", db: Session = Depends(get_db)) -> list[Event]:
    """イベント一覧を返す。

    Args:
        segment_id: 指定時は該当セグメントIDのイベントのみ返す。
        db: DB セッション。

    Returns:
        時刻順に並んだイベント配列。
    """
    q = db.query(Event)
    if segment_id:
        q = q.filter(Event.segment_id == segment_id)
    return q.order_by(Event.timestamp).all()


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: str, db: Session = Depends(get_db)) -> Event:
    """イベントIDを指定して1件取得する。

    Args:
        event_id: イベントID。
        db: DB セッション。

    Returns:
        該当するイベント。
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="イベントが見つかりません")
    return event
