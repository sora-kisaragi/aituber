from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.utils.logging import logger


class PipelineSegmentStateStore:
    """セグメント処理状態をファイルで管理する。"""

    def __init__(self, media_root: str, video_id: str) -> None:
        self.video_id = video_id
        self.state_path = Path(media_root) / video_id / "debug" / "segment_status.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def sync_segments(self, segments: list[Any]) -> dict[str, Any]:
        """現在のセグメント一覧に合わせて状態を同期する。"""
        state = self._load_state()
        current_keys: set[str] = set()

        for index, segment in enumerate(segments):
            key = str(index)
            current_keys.add(key)
            before = state["segments"].get(key, {})
            state["segments"][key] = {
                "index": index,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "storage_path": segment.storage_path,
                "status": before.get("status", "pending"),
                "processed": bool(before.get("processed", False)),
                "last_error": before.get("last_error"),
                "last_segment_id": before.get("last_segment_id"),
                "updated_at": before.get("updated_at"),
            }

        stale_keys = [key for key in state["segments"] if key not in current_keys]
        for key in stale_keys:
            del state["segments"][key]

        self._save_state(state)
        return state

    def failed_indexes(self) -> list[int]:
        """失敗扱いのセグメント index 一覧を返す。"""
        state = self._load_state()
        indexes: list[int] = []
        for key, item in state["segments"].items():
            if item.get("status") == "failed":
                try:
                    indexes.append(int(key))
                except ValueError:
                    logger.error("segment index が整数ではありません: %s", key)
        return sorted(indexes)

    def mark_completed(
        self,
        index: int,
        segment_id: str,
        frame_count: int,
        event_count: int,
    ) -> None:
        """対象セグメントを完了済みとして記録する。"""
        self._mark(
            index=index,
            status="completed",
            processed=True,
            last_error=None,
            extra={
                "last_segment_id": segment_id,
                "frame_count": frame_count,
                "event_count": event_count,
            },
        )

    def mark_failed(self, index: int, error_message: str) -> None:
        """対象セグメントを失敗として記録する。"""
        self._mark(
            index=index,
            status="failed",
            processed=False,
            last_error=error_message,
            extra={},
        )

    def _mark(
        self,
        index: int,
        status: str,
        processed: bool,
        last_error: str | None,
        extra: dict[str, Any],
    ) -> None:
        state = self._load_state()
        key = str(index)
        current = state["segments"].get(key, {"index": index})
        current.update(
            {
                "status": status,
                "processed": processed,
                "last_error": last_error,
                "updated_at": datetime.now(tz=UTC).isoformat(),
            }
        )
        current.update(extra)
        state["segments"][key] = current
        self._save_state(state)

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {
                "video_id": self.video_id,
                "updated_at": datetime.now(tz=UTC).isoformat(),
                "segments": {},
            }

        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("segment 状態ファイル読み込み失敗: %s", e)
            return {
                "video_id": self.video_id,
                "updated_at": datetime.now(tz=UTC).isoformat(),
                "segments": {},
            }

    def _save_state(self, state: dict[str, Any]) -> None:
        state["video_id"] = self.video_id
        state["updated_at"] = datetime.now(tz=UTC).isoformat()
        try:
            self.state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error("segment 状態ファイル保存失敗: %s", e)
