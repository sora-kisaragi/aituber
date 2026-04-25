"""動画分割と代表フレーム抽出のユーティリティ。"""

from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2


@dataclass
class SegmentResult:
    """動画分割結果1件分の情報。"""

    start_time: float
    end_time: float
    segment_type: str = "gameplay"
    storage_path: str = ""


@dataclass
class FrameResult:
    """抽出フレーム1件分の情報。"""

    timestamp: float
    image_path: str
    features: dict[str, Any] = field(default_factory=dict)


class SegmentationService:
    """FFmpeg で動画をセグメント単位に分割する。"""

    def __init__(self, segment_duration: int = 5, media_root: str = "/var/aituber/media") -> None:
        """分割サービスを初期化する。

        Args:
            segment_duration: 1セグメントの長さ（秒）。
            media_root: 分割動画の保存ルート。

        Returns:
            なし。
        """
        self.segment_duration = segment_duration
        self.media_root = Path(media_root)

    def execute(self, video_path: str, video_id: str) -> list[SegmentResult]:
        """動画を `segment_duration` 秒単位に分割し、結果リストを返す。

        Args:
            video_path: 入力動画ファイルパス。
            video_id: 出力先ディレクトリ名に利用する動画ID。

        Returns:
            開始時刻順の分割結果配列。
        """
        duration = self._probe_duration(video_path)
        video_dir = self.media_root / video_id / "segments"
        video_dir.mkdir(parents=True, exist_ok=True)

        segments: list[SegmentResult] = []
        start = 0.0
        index = 0
        while start < duration:
            end = min(start + self.segment_duration, duration)
            seg_path = str(video_dir / f"segment_{index:04d}.mp4")
            self._cut_segment(video_path, start, end - start, seg_path)
            segments.append(
                SegmentResult(
                    start_time=start,
                    end_time=end,
                    segment_type="gameplay",
                    storage_path=seg_path,
                )
            )
            start = end
            index += 1

        return segments

    def _probe_duration(self, video_path: str) -> float:
        """ffprobe で動画再生時間を取得する。"""
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())

    def _cut_segment(self, video_path: str, start: float, duration: float, output: str) -> None:
        """ffmpeg で指定区間のセグメントを切り出す。"""
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                str(start),
                "-i",
                video_path,
                "-t",
                str(duration),
                "-c",
                "copy",
                output,
            ],
            capture_output=True,
            check=True,
        )


class FrameExtractor:
    """各セグメントの中間フレームを OpenCV で抽出する。"""

    def __init__(self, media_root: str = "/var/aituber/media") -> None:
        """フレーム抽出サービスを初期化する。

        Args:
            media_root: 抽出画像の保存ルート。

        Returns:
            なし。
        """
        self.media_root = Path(media_root)

    def extract(
        self,
        video_path: str,
        segment_id: str,
        start_time: float,
        end_time: float,
    ) -> list[FrameResult]:
        """セグメントの中間時刻のフレームを JPEG として保存し、FrameResult を返す。

        Args:
            video_path: 入力動画ファイルパス。
            segment_id: 画像保存先ディレクトリ名に利用するセグメントID。
            start_time: セグメント開始時刻（秒）。
            end_time: セグメント終了時刻（秒）。

        Returns:
            抽出できた場合は1件の `FrameResult` を含む配列。失敗時は空配列。
        """
        mid_time = (start_time + end_time) / 2.0
        frame_dir = self.media_root / segment_id / "frames"
        frame_dir.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_MSEC, mid_time * 1000)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            return []

        image_path = frame_dir / f"frame_{uuid.uuid4().hex[:8]}.jpg"
        cv2.imwrite(str(image_path), frame)

        return [FrameResult(timestamp=mid_time, image_path=str(image_path))]
