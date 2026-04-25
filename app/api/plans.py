"""発話計画（UtterancePlan）参照 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import UtterancePlan
from app.models.schemas import UtterancePlanRead

router = APIRouter()


@router.get("/", response_model=list[UtterancePlanRead])
def list_plans(video_id: str = "", db: Session = Depends(get_db)) -> list[UtterancePlan]:
    """発話計画一覧を返す。

    Args:
        video_id: 指定時は該当動画IDの計画のみ返す。
        db: DB セッション。

    Returns:
        開始時刻順に並んだ発話計画の配列。
    """
    q = db.query(UtterancePlan)
    if video_id:
        q = q.filter(UtterancePlan.video_id == video_id)
    return q.order_by(UtterancePlan.start_time).all()


@router.get("/{plan_id}", response_model=UtterancePlanRead)
def get_plan(plan_id: str, db: Session = Depends(get_db)) -> UtterancePlan:
    """発話計画IDを指定して1件取得する。

    Args:
        plan_id: 発話計画ID。
        db: DB セッション。

    Returns:
        該当する発話計画。
    """
    plan = db.query(UtterancePlan).filter(UtterancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="発話計画が見つかりません")
    return plan
