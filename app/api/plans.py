from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import UtterancePlan
from app.models.schemas import UtterancePlanRead

router = APIRouter()


@router.get("/", response_model=list[UtterancePlanRead])
def list_plans(video_id: str = "", db: Session = Depends(get_db)) -> list[UtterancePlan]:
    q = db.query(UtterancePlan)
    if video_id:
        q = q.filter(UtterancePlan.video_id == video_id)
    return q.order_by(UtterancePlan.start_time).all()


@router.get("/{plan_id}", response_model=UtterancePlanRead)
def get_plan(plan_id: str, db: Session = Depends(get_db)) -> UtterancePlan:
    plan = db.query(UtterancePlan).filter(UtterancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="発話計画が見つかりません")
    return plan
