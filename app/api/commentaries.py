"""実況文（Commentary）参照 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Commentary
from app.models.schemas import CommentaryRead

router = APIRouter()


@router.get("/", response_model=list[CommentaryRead])
def list_commentaries(plan_id: str = "", db: Session = Depends(get_db)) -> list[Commentary]:
    """実況文一覧を返す。

    Args:
        plan_id: 指定時は該当発話計画IDに紐づく実況文のみ返す。
        db: DB セッション。

    Returns:
        条件に一致する実況文の配列。
    """
    q = db.query(Commentary)
    if plan_id:
        q = q.filter(Commentary.utterance_plan_id == plan_id)
    return q.all()


@router.get("/{commentary_id}", response_model=CommentaryRead)
def get_commentary(commentary_id: str, db: Session = Depends(get_db)) -> Commentary:
    """実況文IDを指定して1件取得する。

    Args:
        commentary_id: 実況文ID。
        db: DB セッション。

    Returns:
        該当する実況文。
    """
    com = db.query(Commentary).filter(Commentary.id == commentary_id).first()
    if not com:
        raise HTTPException(status_code=404, detail="実況文が見つかりません")
    return com
