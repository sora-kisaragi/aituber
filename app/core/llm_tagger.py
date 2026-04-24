from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from app.core.tags import normalize_tags

if TYPE_CHECKING:
    from app.clients.llm_client import LLMClient

_SYSTEM_PROMPT = (
    "あなたは動画タグ分類アシスタントです。"
    "与えられたタイトルと既存タグを参考に、次の JSON を必ず返してください。"
    '{"tags_auto_llm": ["genre:*", "game:*", "topic:*"], "tags_suggested_llm": ["candidate:*"]}'
    "説明文は不要です。JSON 以外の文字は出力しないでください。"
)


class LLMTagger:
    """LLM を使って動画タグを生成する。"""

    _SANITIZE_PATTERN = re.compile(r"[^a-z0-9._-]+")
    _JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", re.IGNORECASE)
    _AUTO_PREFIXES = {"genre", "game", "topic"}

    def generate(
        self,
        *,
        video_title: str,
        current_tags: list[str],
        llm_client: LLMClient,
    ) -> dict[str, list[str]]:
        """LLM から自動タグと候補タグを生成して返す。"""
        messages = self._build_messages(video_title, current_tags)
        result = llm_client.complete(messages)
        payload = self._parse_json_payload(result.get("text", ""))

        auto_tags = self._normalize_auto_tags(payload.get("tags_auto_llm"))
        suggested_tags = self._normalize_suggested_tags(payload.get("tags_suggested_llm"))
        return {
            "tags_auto_llm": auto_tags,
            "tags_suggested_llm": suggested_tags,
        }

    def _build_messages(self, video_title: str, current_tags: list[str]) -> list[dict[str, str]]:
        tags_text = ", ".join(current_tags) if current_tags else "(なし)"
        user_prompt = (
            f"動画タイトル: {video_title or '(未設定)'}\n"
            f"既存タグ: {tags_text}\n"
            "JSON 形式のみで返してください。"
        )
        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    def _parse_json_payload(self, raw_text: str) -> dict[str, Any]:
        text = raw_text.strip()
        match = self._JSON_BLOCK_PATTERN.search(text)
        if match:
            text = match.group(1)

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError("LLM タグ出力の JSON 解析に失敗しました") from e

        if not isinstance(payload, dict):
            raise ValueError("LLM タグ出力がオブジェクト形式ではありません")
        return payload

    def _normalize_auto_tags(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []

        raw_tags: list[str] = []
        for raw in value:
            if not isinstance(raw, str):
                continue
            tag = raw.strip().lower()
            if ":" not in tag:
                continue
            prefix, raw_value = tag.split(":", 1)
            if prefix not in self._AUTO_PREFIXES:
                continue
            raw_tags.append(f"{prefix}:{self._sanitize(raw_value)}")

        tags = normalize_tags(raw_tags)
        return [tag for tag in tags if not tag.startswith("candidate:")]

    def _normalize_suggested_tags(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []

        candidate_raw: list[str] = []
        for raw in value:
            if not isinstance(raw, str):
                continue
            tag = raw.strip().lower()
            if not tag:
                continue
            if tag.startswith("candidate:"):
                _, candidate_value = tag.split(":", 1)
                candidate_raw.append(f"candidate:{self._sanitize(candidate_value)}")
                continue
            if ":" in tag:
                tag = tag.split(":", 1)[1]
            candidate_raw.append(f"candidate:{self._sanitize(tag)}")

        tags = normalize_tags(candidate_raw)
        return [tag for tag in tags if tag.startswith("candidate:")]

    def _sanitize(self, value: str) -> str:
        sanitized = self._SANITIZE_PATTERN.sub("_", value.strip().lower())
        return sanitized.strip("_") or "unknown"
