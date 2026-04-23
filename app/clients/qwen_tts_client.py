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
        mode = (mode or self.default_mode).strip()
        speaker = (speaker or self.default_speaker).strip()
        language = (language or self.default_language).strip()
        instruct = instruct or self.default_instruct

        endpoint = self._ENDPOINT_MAP.get(mode, f"/tts/{mode}")
        payload = self._build_payload(endpoint, text, speaker, language, instruct)
        use_form = "voice-clone/profile" in endpoint

        response: httpx.Response | None = None
        for attempt in range(self._MAX_RETRIES):
            try:
                response = httpx.post(
                    f"{self._base_url}{endpoint}",
                    data=payload if use_form else None,
                    json=None if use_form else payload,
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

        self._append_silence(output_path)
        return self._wav_duration(output_path)

    def _build_payload(
        self,
        endpoint: str,
        text: str,
        speaker: str,
        language: str,
        instruct: str = "",
    ) -> dict[str, str]:
        """エンドポイントに応じたリクエストペイロードを組み立てる。

        voice-clone/profile のみ Form、それ以外は JSON body。
        """
        if "voice-clone/profile" in endpoint:
            # Form data: instruct 非対応
            return {"text": text, "profile_name": speaker, "language": language}
        if "voice-design" in endpoint:
            # JSON body: speaker 不要、instruct 必須
            return {"text": text, "instruct": instruct, "language": language}
        # custom-voice: JSON body、instruct は任意
        payload: dict[str, str] = {"text": text, "speaker": speaker, "language": language}
        if instruct:
            payload["instruct"] = instruct
        return payload

    def _append_silence(self, wav_path: str, pad_seconds: float = 0.3) -> None:
        """WAV 末尾に無音フレームを追加する。TTS モデルの末尾クリップを補正する。"""
        with wave.open(wav_path, "rb") as wf:
            params = wf.getparams()
            audio_frames = wf.readframes(wf.getnframes())

        silent_frame_count = int(params.framerate * pad_seconds)
        silent_bytes = b"\x00" * silent_frame_count * params.nchannels * params.sampwidth

        with wave.open(wav_path, "wb") as wf:
            wf.setparams(params)
            wf.writeframes(audio_frames + silent_bytes)

    def _wav_duration(self, wav_path: str) -> float:
        with wave.open(wav_path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
