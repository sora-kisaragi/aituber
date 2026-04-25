"""字幕生成（SRT/WebVTT）ユーティリティ。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SubtitleResult:
    """字幕生成結果。"""

    file_path: str
    start_time: float
    end_time: float
    srt_content: str


class SubtitleService:
    """実況テキストと音声長から SRT 字幕ファイルを生成する。"""

    _MAX_CHARS_PER_LINE = 20

    def generate(
        self,
        text: str,
        start_time: float,
        duration_seconds: float,
        commentary_id: str,
        media_root: str,
    ) -> SubtitleResult:
        """SRT ファイルを生成して保存し、SubtitleResult を返す。

        Args:
            text: 字幕テキスト。
            start_time: 字幕開始時刻（秒）。
            duration_seconds: 字幕表示時間（秒）。
            commentary_id: 保存先ディレクトリ名に使う実況文ID。
            media_root: 字幕保存ルート。

        Returns:
            保存先パスと時刻情報を含む字幕生成結果。
        """
        end_time = start_time + duration_seconds
        lines = self._split_lines(text)
        srt_content = self._build_srt(1, start_time, end_time, lines)

        srt_dir = Path(media_root) / commentary_id
        srt_dir.mkdir(parents=True, exist_ok=True)
        srt_path = srt_dir / "subtitle.srt"
        srt_path.write_text(srt_content, encoding="utf-8")

        return SubtitleResult(
            file_path=str(srt_path),
            start_time=start_time,
            end_time=end_time,
            srt_content=srt_content,
        )

    def _split_lines(self, text: str) -> list[str]:
        """テキストを最大 20 文字で折り返す。

        Args:
            text: 折り返し対象の字幕テキスト。

        Returns:
            最大文字数制約で分割した行配列。
        """
        lines = []
        for i in range(0, max(1, math.ceil(len(text) / self._MAX_CHARS_PER_LINE))):
            chunk = text[i * self._MAX_CHARS_PER_LINE : (i + 1) * self._MAX_CHARS_PER_LINE]
            if chunk:
                lines.append(chunk)
        return lines

    def _build_srt(self, index: int, start: float, end: float, lines: list[str]) -> str:
        """SRT エントリ1件分の文字列を構築する。"""
        return (
            f"{index}\n"
            f"{self._fmt_time(start)} --> {self._fmt_time(end)}\n" + "\n".join(lines) + "\n\n"
        )

    @staticmethod
    def to_webvtt(srt_content: str) -> str:
        """SRT テキストを WebVTT 形式に変換する。

        Args:
            srt_content: SRT 形式テキスト。

        Returns:
            WebVTT 形式テキスト。
        """
        vtt = "WEBVTT\n\n" + srt_content.replace(",", ".", 1)
        # 全タイムスタンプ行のカンマをピリオドに置換
        lines = []
        for line in vtt.splitlines():
            if "-->" in line:
                line = line.replace(",", ".")
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        """秒を `HH:MM:SS,mmm` 形式へ変換する。"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
