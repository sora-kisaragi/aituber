from __future__ import annotations

_store: dict[str, dict[str, object]] = {}


def update_progress(video_id: str, step: str, pct: int, message: str = "") -> None:
    _store[video_id] = {"step": step, "pct": pct, "message": message}


def get_progress(video_id: str) -> dict[str, object] | None:
    return _store.get(video_id)


def clear_progress(video_id: str) -> None:
    _store.pop(video_id, None)
