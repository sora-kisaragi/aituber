from __future__ import annotations

import time
import wave
from pathlib import Path

import httpx


class QwenTTSClient:
    """Qwen TTS API を呼び出して音声ファイルを生成するクライアント。"""

    _MAX_RETRIES = 3
    _RETRY_WAIT = 1.0

    def __init__(
        self,
        base_url: str,
        default_mode: str = "custom_voice",
        default_speaker: str = "ono_anna",
        default_language: str = "japanese",
        default_instruct: str = "",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self.default_mode = default_mode
        self.default_speaker = default_speaker
        self.default_language = default_language
        self.default_instruct = default_instruct

    def synthesize(
        self,
        text: str,
        output_path: str,
        mode: str = "",
        speaker: str = "",
        language: str = "",
        instruct: str = "",
    ) -> float:
        """テキストを音声合成して WAV ファイルを保存し、音声長（秒）を返す。

        最大 3 回リトライする。
        """
        mode = mode or self.default_mode
        speaker = speaker or self.default_speaker
        language = language or self.default_language
        instruct = instruct if instruct is not None else self.default_instruct

        payload = {
            "text": text,
            "speaker": speaker,
            "language": language,
            "instruct": instruct,
        }

        for attempt in range(self._MAX_RETRIES):
            try:
                response = httpx.post(
                    f"{self._base_url}/tts/{mode}",
                    json=payload,
                    timeout=60.0,
                )
                response.raise_for_status()
                break
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                if attempt == self._MAX_RETRIES - 1:
                    raise RuntimeError(f"TTS API 呼び出し失敗 ({attempt + 1} 回試行): {exc}") from exc
                time.sleep(self._RETRY_WAIT)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(response.content)

        return self._wav_duration(output_path)

    def _wav_duration(self, wav_path: str) -> float:
        with wave.open(wav_path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
