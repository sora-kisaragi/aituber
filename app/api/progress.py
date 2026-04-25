"""パイプライン進捗の SSE 配信 API。"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.core.progress_store import get_progress

router = APIRouter()


@router.get("/{video_id}/progress/stream")
async def stream_progress(video_id: str, request: Request) -> EventSourceResponse:
    """process / compose の進捗を SSE でストリーミングする。

    Args:
        video_id: 進捗監視対象動画ID。
        request: クライアント接続状態を判定するリクエスト。

    Returns:
        1秒間隔で進捗JSONを送信する SSE レスポンス。
    """

    async def event_generator():
        """SSE 用の進捗イベントを逐次生成する。

        Args:
            なし。

        Returns:
            `EventSourceResponse` が消費する非同期ジェネレーター。
        """
        while True:
            if await request.is_disconnected():
                break
            data = get_progress(video_id)
            if data is not None:
                yield {"data": json.dumps(data)}
                if int(data.get("pct", 0)) >= 100:
                    break
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())
