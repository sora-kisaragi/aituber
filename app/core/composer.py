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
        self.media_root = Path(media_root)
        self.game_audio_volume = game_audio_volume

    def compose(
        self,
        video_path: str,
        audio_entries: list[AudioEntry],
        srt_path: str | None,
        output_path: str,
    ) -> str:
        """音声ミックスと字幕焼き込みを行い、出力パスを返す。"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        if audio_entries:
            mixed_audio = str(Path(output_path).parent / "mixed_audio.wav")
            self._mix_audio(video_path, audio_entries, mixed_audio)
            source = mixed_audio
        else:
            source = video_path

        if srt_path and Path(srt_path).exists():
            self._burn_subtitles(
                source, srt_path, output_path,
                has_separate_audio=bool(audio_entries),
                video_path=video_path,
            )
        else:
            self._copy_video(
                source, output_path,
                has_separate_audio=bool(audio_entries),
                video_path=video_path,
            )

        return output_path

    def _mix_audio(self, video_path: str, entries: list[AudioEntry], out_wav: str) -> None:
        """元動画音声と実況音声を amix でミックスして WAV に出力する。"""
        inputs = ["-i", video_path]
        filter_parts = [f"[0:a]volume={self.game_audio_volume}[orig]"]

        for i, entry in enumerate(entries, start=1):
            inputs += ["-i", entry.audio_path]
            # 音声の開始位置をオフセットで指定
            filter_parts.append(
                f"[{i}:a]adelay={int(entry.start_time * 1000)}|{int(entry.start_time * 1000)}[d{i}]"
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
        self, source: str, srt_path: str, output: str, *,
        has_separate_audio: bool, video_path: str
    ) -> None:
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
        subtitle_filter = (
            f"subtitles={srt_escaped}"
            ":force_style='Fontname=Noto Sans CJK JP,FontSize=24,PrimaryColour=&H00FFFFFF'"
        )

        if has_separate_audio:
            # 入力0: 元動画（映像）、入力1: ミックス済み音声 WAV
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-i", source,
                    "-map", "0:v",
                    "-map", "1:a",
                    "-vf", subtitle_filter,
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    output,
                ],
                capture_output=True,
                check=True,
            )
        else:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", source,
                    "-vf", subtitle_filter,
                    "-c:v", "libx264",
                    "-c:a", "copy",
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
        if has_separate_audio:
            # 入力0: 元動画（映像）、入力1: ミックス済み音声 WAV
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-i", source,
                    "-map", "0:v",
                    "-map", "1:a",
                    "-c:v", "copy",
                    "-c:a", "aac",
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
