from __future__ import annotations

import base64
import json
import logging
from typing import Any

import cv2
from openai import OpenAI

from app.core.vision import VisionAnalysis

logger = logging.getLogger(__name__)

_PROMPT = """\
You are a game scene analyzer. Analyze this game screenshot and return ONLY a JSON object with these fields:
- scene_summary: brief Japanese description of what is happening (例: "戦闘中", "ボスとの激しい攻防")
- objects: list of key entities visible (例: ["プレイヤー", "敵", "ボス"])
- actions: list of ongoing actions in Japanese (例: ["攻撃", "移動", "待機", "スコア変化"])
- ui_state: list of visible UI elements (例: ["HPバー", "スコア表示"])
- confidence: float 0.0-1.0 representing how exciting or important this moment is

Return ONLY valid JSON. No markdown fences, no explanation."""


class VLMClient:
    """Vision Language Model クライアント。フレーム画像を解析して VisionAnalysis を返す。"""

    _RESIZE_WIDTH = 640

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._model = model

    def analyze(self, image_path: str) -> VisionAnalysis:
        """フレーム画像を VLM で解析して VisionAnalysis を返す。失敗時はダミーにフォールバック。"""
        try:
            b64 = self._encode_image(image_path)
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                        ],
                    }
                ],
                max_tokens=512,
                temperature=0.1,
            )
            raw = response.choices[0].message.content or ""
            return self._parse(raw)
        except Exception:
            logger.exception("VLM 解析失敗: %s", image_path)
            return VisionAnalysis(scene_summary="解析失敗", confidence=0.3)

    def _encode_image(self, image_path: str) -> str:
        """画像を JPEG に変換して base64 エンコードする。長辺を _RESIZE_WIDTH に縮小する。"""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"画像読み込み失敗: {image_path}")
        h, w = img.shape[:2]
        if w > self._RESIZE_WIDTH:
            scale = self._RESIZE_WIDTH / w
            img = cv2.resize(img, (self._RESIZE_WIDTH, int(h * scale)))
        _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return base64.b64encode(buf.tobytes()).decode()

    def _parse(self, raw: str) -> VisionAnalysis:
        """VLM レスポンスを VisionAnalysis にパースする。失敗時はテキストをそのまま使う。"""
        try:
            text = raw.strip()
            # マークダウンコードブロックを除去
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            data: dict[str, Any] = json.loads(text)
            return VisionAnalysis(
                scene_summary=str(data.get("scene_summary", "")),
                objects=list(data.get("objects", [])),
                actions=list(data.get("actions", [])),
                ui_state=list(data.get("ui_state", [])),
                confidence=float(data.get("confidence", 0.5)),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            logger.warning("VLM レスポンスのパース失敗: %s", raw[:200])
            return VisionAnalysis(scene_summary=raw[:80], confidence=0.5)
