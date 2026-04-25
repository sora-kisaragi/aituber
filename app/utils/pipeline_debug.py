from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.utils.logging import logger


class PipelineDebugRecorder:
    """パイプラインの入出力とデバッグ情報をファイルへ保存する。"""

    def __init__(self, media_root: str, video_id: str) -> None:
        self.video_id = video_id
        self.debug_dir = Path(media_root) / video_id / "debug"
        self.steps_dir = self.debug_dir / "steps"
        self.segment_log_path = self.debug_dir / "segments_debug.jsonl"
        self.steps_dir.mkdir(parents=True, exist_ok=True)
        self._step_index = 0

    def save_step_io(
        self,
        step_name: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
    ) -> str | None:
        """ステップ入出力を JSON ファイルとして保存する。"""
        self._step_index += 1
        file_name = f"{self._step_index:02d}_{_sanitize_step_name(step_name)}.json"
        output_path = self.steps_dir / file_name
        payload = {
            "video_id": self.video_id,
            "step": step_name,
            "recorded_at": datetime.now(tz=UTC).isoformat(),
            "input": _to_jsonable(input_data),
            "output": _to_jsonable(output_data),
        }
        return self._write_json_file(output_path, payload, label=f"step={step_name}")

    def append_segment_debug(
        self,
        segment_index: int,
        segment_id: str,
        stage: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
    ) -> str | None:
        """セグメント単位のデバッグ情報を JSONL 形式で追記する。"""
        payload = {
            "video_id": self.video_id,
            "segment_index": segment_index,
            "segment_id": segment_id,
            "stage": stage,
            "recorded_at": datetime.now(tz=UTC).isoformat(),
            "input": _to_jsonable(input_data),
            "output": _to_jsonable(output_data),
        }
        try:
            with open(self.segment_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False))
                f.write("\n")
        except Exception as e:
            logger.error("segment デバッグログ保存失敗(%s): %s", stage, e)
            return None
        logger.debug(
            "segment デバッグログ保存: stage=%s segment=%s path=%s",
            stage,
            segment_id,
            self.segment_log_path,
        )
        return str(self.segment_log_path)

    def _write_json_file(
        self, output_path: Path, payload: dict[str, Any], label: str
    ) -> str | None:
        try:
            output_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error("デバッグ入出力保存失敗(%s): %s", label, e)
            return None
        logger.debug("デバッグ入出力保存: %s", output_path)
        return str(output_path)


def _sanitize_step_name(step_name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", step_name).strip("_")
    return normalized or "step"


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Path | UUID):
        return str(value)
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [_to_jsonable(v) for v in value]

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _to_jsonable(model_dump())
        except Exception:
            return repr(value)

    to_dict = getattr(value, "dict", None)
    if callable(to_dict):
        try:
            return _to_jsonable(to_dict())
        except Exception:
            return repr(value)

    if hasattr(value, "__dict__"):
        try:
            return _to_jsonable(vars(value))
        except Exception:
            return repr(value)

    return repr(value)
