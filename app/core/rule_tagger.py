from __future__ import annotations

import re


class RuleTagger:
    """設定値と動画メタから機械的タグを生成する。"""

    _SANITIZE_PATTERN = re.compile(r"[^a-z0-9._-]+")

    def generate(
        self,
        *,
        tts_mode: str,
        llm_model: str,
        vlm_model: str,
        duration_seconds: float | None,
        fps: float | None,
    ) -> list[str]:
        tags: list[str] = []

        tags.append(f"cfg:tts_mode:{self._sanitize(tts_mode)}")
        tags.append(f"cfg:llm_model:{self._sanitize(llm_model)}")
        tags.append(f"cfg:vlm_model:{self._sanitize(vlm_model)}")
        tags.append(f"video:length:{self._length_bucket(duration_seconds)}")
        tags.append(f"video:fps:{self._fps_bucket(fps)}")
        return tags

    def _sanitize(self, value: str) -> str:
        normalized = self._SANITIZE_PATTERN.sub("_", value.strip().lower())
        return normalized.strip("_") or "unknown"

    def _length_bucket(self, duration_seconds: float | None) -> str:
        if duration_seconds is None or duration_seconds <= 0:
            return "unknown"
        if duration_seconds < 60:
            return "short"
        if duration_seconds < 300:
            return "medium"
        return "long"

    def _fps_bucket(self, fps: float | None) -> str:
        if fps is None or fps <= 0:
            return "unknown"
        return str(int(round(fps)))
