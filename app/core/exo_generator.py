"""AviUtl 拡張編集 .exo ファイルジェネレータ。

生成する .exo の層構成:
  Layer 1 : 元動画（映像 + 元音声）
  Layer 2 : 実況音声 WAV（発話ごとに配置）
  Layer 3 : 字幕テキスト（発話ごとに配置）

フレーム番号は 1-indexed。パスは ZIP 展開後の相対パス（Windows バックスラッシュ）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class ExoEntry:
    """1 発話分のデータ。"""

    audio_file: str  # ZIP 内相対パス（例: audio\\xxx.wav）
    start_time: float  # 発話開始秒
    duration_seconds: float
    text: str


@dataclass
class ExoConfig:
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    total_duration: float = 0.0
    audio_rate: int = 44100
    audio_ch: int = 2
    font: str = "MS UI Gothic"
    font_size: int = 34
    font_color: str = "ffffff"


class ExoGenerator:
    """AviUtl 拡張編集形式の .exo テキストを生成する。"""

    def generate(
        self,
        video_file: str,
        entries: list[ExoEntry],
        config: ExoConfig,
    ) -> bytes:
        """exo ファイルの内容を Shift-JIS バイト列で返す。"""
        fps = config.fps
        total_frames = max(1, math.ceil(config.total_duration * fps))
        rate, scale = self._fps_fraction(fps)

        blocks: list[str] = []

        blocks.append(
            self._header(
                config.width,
                config.height,
                rate,
                scale,
                total_frames,
                config.audio_rate,
                config.audio_ch,
            )
        )

        obj_idx = 0

        # Layer 1: 元動画
        blocks.append(self._video_block(obj_idx, 1, total_frames, layer=1, file=video_file))
        obj_idx += 1

        # Layer 2: 実況音声（発話ごと）
        for entry in entries:
            sf, ef = self._frames(entry.start_time, entry.duration_seconds, fps)
            blocks.append(self._audio_block(obj_idx, sf, ef, layer=2, file=entry.audio_file))
            obj_idx += 1

        # Layer 3: 字幕テキスト（発話ごと）
        for entry in entries:
            sf, ef = self._frames(entry.start_time, entry.duration_seconds, fps)
            blocks.append(
                self._text_block(obj_idx, sf, ef, layer=3, text=entry.text, config=config)
            )
            obj_idx += 1

        content = "\r\n".join(blocks)
        return content.encode("shift-jis", errors="replace")

    # ── ブロック生成 ────────────────────────────────────────────────────────

    def _header(
        self,
        width: int,
        height: int,
        rate: int,
        scale: int,
        length: int,
        audio_rate: int,
        audio_ch: int,
    ) -> str:
        return "\r\n".join(
            [
                "[exedit]",
                f"width={width}",
                f"height={height}",
                f"rate={rate}",
                f"scale={scale}",
                f"length={length}",
                f"audio_rate={audio_rate}",
                f"audio_ch={audio_ch}",
            ]
        )

    def _video_block(self, idx: int, start: int, end: int, layer: int, file: str) -> str:
        return "\r\n".join(
            [
                f"[{idx}]",
                f"start={start}",
                f"end={end}",
                f"layer={layer}",
                "overlay=1",
                "audio=1",
                "",
                f"[{idx}.0]",
                "_name=動画ファイル",
                "再生位置=0.00",
                "再生速度=100.0",
                "ループ再生=0",
                "アルファチャンネルを読み込む=0",
                f"file={file}",
            ]
        )

    def _audio_block(self, idx: int, start: int, end: int, layer: int, file: str) -> str:
        return "\r\n".join(
            [
                f"[{idx}]",
                f"start={start}",
                f"end={end}",
                f"layer={layer}",
                "overlay=1",
                "audio=1",
                "",
                f"[{idx}.0]",
                "_name=音声ファイル",
                "再生位置=0.00",
                "再生速度=100.0",
                "ループ再生=0",
                f"file={file}",
            ]
        )

    def _text_block(
        self,
        idx: int,
        start: int,
        end: int,
        layer: int,
        text: str,
        config: ExoConfig,
    ) -> str:
        return "\r\n".join(
            [
                f"[{idx}]",
                f"start={start}",
                f"end={end}",
                f"layer={layer}",
                "overlay=1",
                "audio=0",
                "",
                f"[{idx}.0]",
                "_name=テキスト",
                f"サイズ={config.font_size}",
                "表示速度=0.0",
                "文字毎に個別オブジェクト=0",
                "移動座標上に表示する=0",
                "自動スクロール=0",
                "B=0",
                "I=0",
                "type=0",
                "autoadjust=0",
                "soft=0",
                "monospace=0",
                "align=4",
                "spacing_x=0",
                "spacing_y=0",
                "precision=1",
                f"color={config.font_color}",
                "color2=000000",
                f"font={config.font}",
                f"text={self._encode_text(text)}",
            ]
        )

    # ── ユーティリティ ──────────────────────────────────────────────────────

    def _frames(self, start_time: float, duration: float, fps: float) -> tuple[int, int]:
        """開始・終了フレーム番号（1-indexed）を返す。"""
        sf = max(1, round(start_time * fps))
        ef = max(sf, round((start_time + duration) * fps))
        return sf, ef

    def _fps_fraction(self, fps: float) -> tuple[int, int]:
        """fps を (rate, scale) の整数比で返す。"""
        common = {29.97: (30000, 1001), 23.976: (24000, 1001), 59.94: (60000, 1001)}
        for f, (r, s) in common.items():
            if abs(fps - f) < 0.01:
                return r, s
        return round(fps), 1

    def _encode_text(self, text: str) -> str:
        """テキストを UTF-16LE hex 文字列に変換する（4096 文字固定長、末尾ゼロ埋め）。"""
        encoded = text.encode("utf-16-le")
        hex_str = encoded.hex().upper()
        return hex_str.ljust(4096, "0")
