from __future__ import annotations

import time
import wave
from pathlib import Path

import httpx


class QwenTTSClient:
    """Qwen TTS API を呼び出して音声ファイルを生成するクライアント。

    モードと対応エンドポイント:
      - voice_clone_profile : POST /tts/voice-clone/profile  (保存済み .pt プロファイル使用)
      - custom_voice        : POST /tts/custom-voice          (プリセット話者)
      - voice_design        : POST /tts/voice-design          (パラメータ指定)
    """

    _MAX_RETRIES = 3
    _RETRY_WAIT = 1.0

    _ENDPOINT_MAP: dict[str, str] = {
        "voice_clone_profile": "/tts/voice-clone/profile",
        "voice_clone": "/tts/voice-clone/profile",
        "custom_voice": "/tts/custom-voice",
        "voice_design": "/tts/voice-design",
    }

    def __init__(
        self,
        base_url: str,
        default_mode: str = "voice_clone_profile",
        default_speaker: str = "default.pt",
        default_language: str = "auto",
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

        最大 3 回リトライする。リクエストは multipart/form-data で送信する。
        """
        mode = mode or self.default_mode
        speaker = speaker or self.default_speaker
        language = language or self.default_language
        instruct = instruct or self.default_instruct

        endpoint = self._ENDPOINT_MAP.get(mode, f"/tts/{mode}")
        form_data = self._build_form(endpoint, text, speaker, language, instruct)

        response: httpx.Response | None = None
        for attempt in range(self._MAX_RETRIES):
            try:
                response = httpx.post(
                    f"{self._base_url}{endpoint}",
                    data=form_data,
                    timeout=60.0,
                )
                response.raise_for_status()
                break
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                if attempt == self._MAX_RETRIES - 1:
                    raise RuntimeError(
                        f"TTS API 呼び出し失敗 ({attempt + 1} 回試行): {exc}"
                    ) from exc
                time.sleep(self._RETRY_WAIT)

        assert response is not None
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(response.content)

        return self._wav_duration(output_path)

    def _build_form(
        self,
        endpoint: str,
        text: str,
        speaker: str,
        language: str,
        instruct: str = "",
    ) -> dict[str, str]:
        """エンドポイントに応じた form-data を組み立てる。"""
        if "voice-clone/profile" in endpoint:
            # instruct 非対応: profile_name (.pt 拡張子ごと) のみ
            return {"text": text, "profile_name": speaker, "language": language}
        if "voice-design" in endpoint:
            # speaker 不要、instruct 必須
            return {"text": text, "instruct": instruct, "language": language}
        # custom-voice: instruct は任意
        form: dict[str, str] = {"text": text, "speaker": speaker, "language": language}
        if instruct:
            form["instruct"] = instruct
        return form

    def _wav_duration(self, wav_path: str) -> float:
        with wave.open(wav_path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
