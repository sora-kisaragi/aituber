"""設定値・動画メタ情報からルールベースタグを生成する。"""

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
        """設定値と動画情報から system タグ群を生成する。

        Args:
            tts_mode: TTS モード設定値。
            llm_model: LLM モデル名。
            vlm_model: VLM モデル名。
            duration_seconds: 動画再生時間（秒）。
            fps: 動画FPS。

        Returns:
            taxonomy に沿ったルールタグの配列。
        """
        tags: list[str] = []

        tags.append(f"cfg:tts_mode:{self._sanitize(tts_mode)}")
        tags.append(f"cfg:llm_model:{self._sanitize(llm_model)}")
        tags.append(f"cfg:vlm_model:{self._sanitize(vlm_model)}")
        tags.append(f"video:length:{self._length_bucket(duration_seconds)}")
        tags.append(f"video:fps:{self._fps_bucket(fps)}")
        return tags

    def _sanitize(self, value: str) -> str:
        """タグ値として使える文字列へ正規化する。"""
        normalized = self._SANITIZE_PATTERN.sub("_", value.strip().lower())
        return normalized.strip("_") or "unknown"

    def _length_bucket(self, duration_seconds: float | None) -> str:
        """動画長を `short/medium/long/unknown` に分類する。"""
        if duration_seconds is None or duration_seconds <= 0:
            return "unknown"
        if duration_seconds < 60:
            return "short"
        if duration_seconds < 300:
            return "medium"
        return "long"

    def _fps_bucket(self, fps: float | None) -> str:
        """FPS を整数化したバケット文字列へ変換する。"""
        if fps is None or fps <= 0:
            return "unknown"
        return str(int(round(fps)))
