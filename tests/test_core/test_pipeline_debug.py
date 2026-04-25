from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.utils.pipeline_debug import PipelineDebugRecorder


@dataclass
class _DummyObject:
    label: str


def test_save_step_io_with_dataclass_and_path_writes_json(tmp_path: Path) -> None:
    recorder = PipelineDebugRecorder(str(tmp_path), "video-001")
    output_path = recorder.save_step_io(
        step_name="segment step",
        input_data={
            "obj": _DummyObject(label="ok"),
            "path": tmp_path / "frames" / "frame_0001.jpg",
        },
        output_data={"result": "saved"},
    )

    assert output_path is not None
    payload = json.loads(Path(output_path).read_text(encoding="utf-8"))
    assert payload["video_id"] == "video-001"
    assert payload["step"] == "segment step"
    assert payload["input"]["obj"]["label"] == "ok"
    assert payload["input"]["path"].endswith("frame_0001.jpg")
    assert payload["output"]["result"] == "saved"


def test_append_segment_debug_when_called_twice_appends_jsonl(tmp_path: Path) -> None:
    recorder = PipelineDebugRecorder(str(tmp_path), "video-xyz")
    log_path = recorder.append_segment_debug(
        segment_index=0,
        segment_id="seg-a",
        stage="frame_extraction",
        input_data={"start_time": 0.0},
        output_data={"frame_count": 1},
    )
    recorder.append_segment_debug(
        segment_index=0,
        segment_id="seg-a",
        stage="event_generation",
        input_data={"analysis_count": 1},
        output_data={"event_count": 2},
    )

    assert log_path is not None
    lines = Path(log_path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first_payload = json.loads(lines[0])
    second_payload = json.loads(lines[1])
    assert first_payload["stage"] == "frame_extraction"
    assert first_payload["output"]["frame_count"] == 1
    assert second_payload["stage"] == "event_generation"
    assert second_payload["output"]["event_count"] == 2
