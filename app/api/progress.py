from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.core.progress_store import get_progress

router = APIRouter()


@router.get("/{video_id}/progress/stream")
async def stream_progress(video_id: str, request: Request) -> EventSourceResponse:
    """process / compose の進捗を SSE でストリーミングする。"""

    async def event_generator():
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
