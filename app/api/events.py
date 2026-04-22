from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Event
from app.models.schemas import EventRead

router = APIRouter()


@router.get("/", response_model=list[EventRead])
def list_events(segment_id: str = "", db: Session = Depends(get_db)) -> list[Event]:
    q = db.query(Event)
    if segment_id:
        q = q.filter(Event.segment_id == segment_id)
    return q.order_by(Event.timestamp).all()


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: str, db: Session = Depends(get_db)) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="イベントが見つかりません")
    return event
