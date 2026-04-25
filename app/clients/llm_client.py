"""OpenAI 互換 API を利用する LLM クライアント。"""

from __future__ import annotations

from typing import Any

from openai import OpenAI


class LLMClient:
    """OpenAI 互換 API を使って実況文を生成するクライアント。"""

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        """LLM クライアントを初期化する。

        Args:
            base_url: OpenAI 互換 API のベース URL。
            api_key: API 認証キー。
            model: 補完に使用するモデル名。

        Returns:
            なし。API クライアントと利用モデル名を保持する。
        """
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._model = model

    def complete(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """チャット補完を実行し、整形済み結果を返す。

        Args:
            messages: Chat Completions 形式のメッセージ配列。

        Returns:
            `text`（生成テキスト）と `raw`（レスポンス全体）を持つ辞書。
        """
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
