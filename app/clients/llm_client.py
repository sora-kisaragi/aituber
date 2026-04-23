from __future__ import annotations

from typing import Any

from openai import OpenAI


class LLMClient:
    """OpenAI 互換 API を使って実況文を生成するクライアント。"""

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._model = model

    def complete(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """チャット補完を実行し、生成テキストと生レスポンスを返す。"""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=200,
            temperature=0.8,
        )
        text = response.choices[0].message.content or ""
        return {
            "text": text.strip(),
            "raw": response.model_dump(),
        }
