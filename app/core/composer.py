"""実況音声・字幕を FFmpeg で合成する。"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AudioEntry:
    """合成時に必要な音声情報。"""

    audio_path: str
    start_time: float
    duration_seconds: float


class Composer:
    """FFmpeg で実況音声・字幕を元動画にミックスして最終 mp4 を出力する。"""

    def __init__(
        self,
        media_root: str = "/var/aituber/media",
        game_audio_volume: float = 0.3,
    ) -> None:
        """Composer を初期化する。

        Args:
            media_root: 一時成果物の保存ルート。
            game_audio_volume: 元ゲーム音声に適用する音量倍率。

        Returns:
            なし。
        """
        self.media_root = Path(media_root)
        self.game_audio_volume = game_audio_volume

    def compose(
        self,
        video_path: str,
        audio_entries: list[AudioEntry],
        srt_path: str | None,
        output_path: str,
    ) -> str:
        """音声ミックスと字幕焼き込みを行い、出力パスを返す。

        Args:
            video_path: 元動画ファイルパス。
            audio_entries: 発話音声エントリ配列。
            srt_path: 字幕ファイルパス（未指定時は字幕なし）。
            output_path: 出力動画ファイルパス。

        Returns:
            最終出力動画パス。
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        if audio_entries:
            safe_audio_entries = self.schedule_entries(audio_entries)
            mixed_audio = str(Path(output_path).parent / "mixed_audio.wav")
            self._mix_audio(video_path, safe_audio_entries, mixed_audio)
            source = mixed_audio
        else:
            source = video_path

        if srt_path and Path(srt_path).exists():
            self._burn_subtitles(
                source,
                srt_path,
                output_path,
                has_separate_audio=bool(audio_entries),
                video_path=video_path,
            )
        else:
            self._copy_video(
                source,
                output_path,
                has_separate_audio=bool(audio_entries),
                video_path=video_path,
            )

        return output_path

    def schedule_entries(
        self,
        entries: list[AudioEntry],
        min_gap_seconds: float = 0.0,
        overlap_strategy: str = "shift",
        min_keep_duration_seconds: float = 0.3,
    ) -> list[AudioEntry]:
        """重複しないように音声エントリ開始時刻を正規化する。

        Args:
            entries: 正規化対象の音声エントリ配列。
            min_gap_seconds: 音声間に確保する最小ギャップ（秒）。
            overlap_strategy: 重複時の解消戦略（`shift` / `clip_previous`）。
            min_keep_duration_seconds: `clip_previous` 時に保持する最小発話長（秒）。

        Returns:
            重複解消後の音声エントリ配列。
        """
        if not entries:
            return []

        sorted_entries = sorted(entries, key=lambda e: e.start_time)
        gap = max(0.0, min_gap_seconds)
        min_keep = max(0.0, min_keep_duration_seconds)

        if overlap_strategy == "clip_previous":
            normalized_clip: list[AudioEntry] = []
            for entry in sorted_entries:
                current = AudioEntry(
                    audio_path=entry.audio_path,
                    start_time=max(0.0, entry.start_time),
                    duration_seconds=max(0.0, entry.duration_seconds),
                )
                if normalized_clip:
                    prev = normalized_clip[-1]
                    prev_end = prev.start_time + prev.duration_seconds
                    overlap_limit = current.start_time - gap
                    if prev_end > overlap_limit:
                        allowed_duration = max(0.0, overlap_limit - prev.start_time)
                        # 次発話を優先しつつ、短すぎる切れ端は自然さを損なうため破棄する。
                        prev.duration_seconds = (
                            allowed_duration if allowed_duration >= min_keep else 0.0
                        )
                normalized_clip.append(current)
            return normalized_clip

        next_available = 0.0
        normalized_shift: list[AudioEntry] = []
        for entry in sorted_entries:
            start_time = max(entry.start_time, next_available)
            duration = max(0.0, entry.duration_seconds)
            normalized_shift.append(
                AudioEntry(
                    audio_path=entry.audio_path,
                    start_time=start_time,
                    duration_seconds=duration,
                )
            )
            next_available = start_time + duration + gap
        return normalized_shift

    def _mix_audio(self, video_path: str, entries: list[AudioEntry], out_wav: str) -> None:
        """元動画音声と実況音声を amix でミックスして WAV に出力する。

        Args:
            video_path: 元動画パス（0番入力）。
            entries: 合成対象の実況音声エントリ。
            out_wav: ミックス済み WAV の出力先。

        Returns:
            なし。`out_wav` へミックス結果を書き込む。
        """
        inputs = ["-i", video_path]
        filter_parts = [f"[0:a]volume={self.game_audio_volume}[orig]"]

        for i, entry in enumerate(entries, start=1):
            inputs += ["-i", entry.audio_path]
            trimmed_duration = max(0.0, entry.duration_seconds)
            # 音声の開始位置をオフセットで指定
            filter_parts.append(
                f"[{i}:a]atrim=0:{trimmed_duration:.3f},asetpts=PTS-STARTPTS,"
                f"adelay={int(entry.start_time * 1000)}|{int(entry.start_time * 1000)}[d{i}]"
            )

        mix_inputs = "[orig]" + "".join(f"[d{i}]" for i in range(1, len(entries) + 1))
        filter_parts.append(f"{mix_inputs}amix=inputs={len(entries) + 1}:duration=longest[out]")
        filter_complex = ";".join(filter_parts)

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                *inputs,
                "-filter_complex",
                filter_complex,
                "-map",
                "[out]",
                out_wav,
            ],
            capture_output=True,
            check=True,
        )

    def _burn_subtitles(
        self, source: str, srt_path: str, output: str, *, has_separate_audio: bool, video_path: str
    ) -> None:
        """字幕を焼き込んだ動画を書き出す。"""
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
        subtitle_filter = (
            f"subtitles={srt_escaped}"
            ":force_style='Fontname=Noto Sans CJK JP,FontSize=24,PrimaryColour=&H00FFFFFF'"
        )

        if has_separate_audio:
            # 入力0: 元動画（映像）、入力1: ミックス済み音声 WAV
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    video_path,
                    "-i",
                    source,
                    "-map",
                    "0:v",
                    "-map",
                    "1:a",
                    "-vf",
                    subtitle_filter,
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    output,
                ],
                capture_output=True,
                check=True,
            )
        else:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    source,
                    "-vf",
                    subtitle_filter,
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "copy",
                    output,
                ],
                capture_output=True,
                check=True,
            )

    def _copy_video(
        self,
        source: str,
        output: str,
        *,
        has_separate_audio: bool,
        video_path: str,
    ) -> None:
        """字幕なしで映像・音声を結合して出力する。"""
        if has_separate_audio:
            # 入力0: 元動画（映像）、入力1: ミックス済み音声 WAV
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    video_path,
                    "-i",
                    source,
                    "-map",
                    "0:v",
                    "-map",
                    "1:a",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    output,
                ],
                capture_output=True,
                check=True,
            )
        else:
            subprocess.run(
                ["ffmpeg", "-y", "-i", source, "-c", "copy", output],
                capture_output=True,
                check=True,
            )
