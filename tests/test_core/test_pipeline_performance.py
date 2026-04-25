from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.utils.pipeline_performance import PipelinePerformanceRecorder


def test_measure_and_finalize_writes_performance_file(tmp_path: Path) -> None:
    recorder = PipelinePerformanceRecorder(str(tmp_path), "video-001")

    with recorder.measure("segmentation", {"segment_duration": 5}):
        pass
    recorder.checkpoint("after_segmentation", {"segment_count": 2})
    output_path = recorder.finalize({"ok": True})

    assert output_path is not None
    payload = json.loads(Path(output_path).read_text(encoding="utf-8"))
    assert payload["video_id"] == "video-001"
    assert payload["summary"]["ok"] is True
    assert len(payload["steps"]) == 1
    assert payload["steps"][0]["name"] == "segmentation"
    assert payload["steps"][0]["status"] == "ok"
    assert len(payload["checkpoints"]) == 1
    assert payload["checkpoints"][0]["label"] == "after_segmentation"


def test_measure_when_error_occurs_records_error_status(tmp_path: Path) -> None:
    recorder = PipelinePerformanceRecorder(str(tmp_path), "video-002")

    with pytest.raises(RuntimeError, match="boom"):
        with recorder.measure("segment_pipeline"):
            raise RuntimeError("boom")

    payload = json.loads((tmp_path / "video-002" / "debug" / "performance.json").read_text())
    assert payload["steps"][0]["name"] == "segment_pipeline"
    assert payload["steps"][0]["status"] == "error"
    assert payload["steps"][0]["error"] == "boom"
