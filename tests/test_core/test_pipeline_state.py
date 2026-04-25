from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from app.utils.pipeline_state import PipelineSegmentStateStore


def test_sync_segments_creates_pending_entries(tmp_path: Path) -> None:
    store = PipelineSegmentStateStore(str(tmp_path), "video-1")
    segments = [
        SimpleNamespace(start_time=0.0, end_time=5.0, storage_path="/tmp/seg0.mp4"),
        SimpleNamespace(start_time=5.0, end_time=10.0, storage_path="/tmp/seg1.mp4"),
    ]

    state = store.sync_segments(segments)

    assert sorted(state["segments"].keys()) == ["0", "1"]
    assert state["segments"]["0"]["status"] == "pending"
    assert state["segments"]["0"]["processed"] is False
    assert state["segments"]["1"]["start_time"] == 5.0


def test_mark_failed_and_completed_updates_status(tmp_path: Path) -> None:
    store = PipelineSegmentStateStore(str(tmp_path), "video-2")
    segments = [SimpleNamespace(start_time=0.0, end_time=5.0, storage_path="/tmp/seg0.mp4")]
    store.sync_segments(segments)

    store.mark_failed(0, "vision timeout")
    assert store.failed_indexes() == [0]

    store.mark_completed(0, segment_id="seg-uuid", frame_count=2, event_count=3)

    payload = json.loads((tmp_path / "video-2" / "debug" / "segment_status.json").read_text())
    entry = payload["segments"]["0"]
    assert entry["status"] == "completed"
    assert entry["processed"] is True
    assert entry["last_error"] is None
    assert entry["last_segment_id"] == "seg-uuid"
    assert entry["frame_count"] == 2
    assert entry["event_count"] == 3
