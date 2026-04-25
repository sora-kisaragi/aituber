"""LLM を利用して動画タグを推定・正規化する。"""

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
    '{"tags_auto_llm": ["genre:*", "game:*", "topic:*", "scene:*", "situation:*", '
    '"place:*", "environment:*", "time:*", "weather:*"], '
    '"tags_suggested_llm": ["candidate:*"]}'
    "ゲーム動画ではゲーム名・ジャンル・場面を優先し、"
    "非ゲーム動画では場所らしさ・環境属性（屋内外/時間帯/天候）を含めてください。"
    '同義語の重複や "unknown" "other" のような曖昧語は避けてください。'
    "説明文は不要です。JSON 以外の文字は出力しないでください。"
)


class LLMTagger:
    """LLM を使って動画タグを生成する。"""

    _SANITIZE_PATTERN = re.compile(r"[^a-z0-9._-]+")
    _JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", re.IGNORECASE)
    _AUTO_PREFIXES = {
        "genre",
        "game",
        "topic",
        "scene",
        "situation",
        "place",
        "environment",
        "time",
        "weather",
    }
    _NOISE_VALUES = {"unknown", "other", "misc", "none", "null", "n_a"}
    _MAX_AUTO_TAGS = 12
    _MAX_SUGGESTED_TAGS = 12
    _MAX_PER_PREFIX = 3

    def generate(
        self,
        *,
        video_title: str,
        current_tags: list[str],
        llm_client: LLMClient,
    ) -> dict[str, list[str]]:
        """LLM から自動タグと候補タグを生成して返す。

        Args:
            video_title: 対象動画タイトル。
            current_tags: 既存タグ（文脈ヒントとして利用）。
            llm_client: タグ生成に使う LLM クライアント。

        Returns:
            `tags_auto_llm` と `tags_suggested_llm` を持つ辞書。
        """
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
        """タグ生成用のプロンプトメッセージを組み立てる。"""
        tags_text = ", ".join(current_tags) if current_tags else "(なし)"
        user_prompt = (
            f"動画タイトル: {video_title or '(未設定)'}\n"
            f"既存タグ: {tags_text}\n"
            "命名方針: SNSで一般的に伝わる短い語を使い、同義語の乱立を避けること。\n"
            "自動タグは 6〜12 件を目安に推定すること。\n"
            "JSON 形式のみで返してください。"
        )
        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    def _parse_json_payload(self, raw_text: str) -> dict[str, Any]:
        """LLM 出力文字列から JSON オブジェクトを抽出して返す。"""
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
        """`tags_auto_llm` 候補を taxonomy 準拠形式へ正規化する。"""
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
            suffix = self._sanitize(raw_value)
            if self._is_noise_value(suffix):
                continue
            raw_tags.append(f"{prefix}:{suffix}")

        tags = normalize_tags(raw_tags)
        auto_tags = [tag for tag in tags if not tag.startswith("candidate:")]
        return self._apply_auto_tag_limits(auto_tags)

    def _normalize_suggested_tags(self, value: Any) -> list[str]:
        """`tags_suggested_llm` 候補を `candidate:*` 形式へ正規化する。"""
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
                suffix = self._sanitize(candidate_value)
                if self._is_noise_value(suffix):
                    continue
                candidate_raw.append(f"candidate:{suffix}")
                continue
            if ":" in tag:
                tag = tag.split(":", 1)[1]
            suffix = self._sanitize(tag)
            if self._is_noise_value(suffix):
                continue
            candidate_raw.append(f"candidate:{suffix}")

        tags = normalize_tags(candidate_raw)
        suggested = [tag for tag in tags if tag.startswith("candidate:")]
        return suggested[: self._MAX_SUGGESTED_TAGS]

    def _sanitize(self, value: str) -> str:
        """タグ値から許容文字以外を除去して整形する。"""
        sanitized = self._SANITIZE_PATTERN.sub("_", value.strip().lower())
        return sanitized.strip("_") or "unknown"

    def _is_noise_value(self, value: str) -> bool:
        """ノイズ語として除外すべきタグ値か判定する。"""
        return value in self._NOISE_VALUES

    def _apply_auto_tag_limits(self, tags: list[str]) -> list[str]:
        """自動タグ件数とプレフィックス偏りを制限する。"""
        limited: list[str] = []
        by_prefix_count: dict[str, int] = {}

        for tag in tags:
            if ":" not in tag:
                continue
            prefix = tag.split(":", 1)[0]
            used = by_prefix_count.get(prefix, 0)
            if used >= self._MAX_PER_PREFIX:
                continue
            limited.append(tag)
            by_prefix_count[prefix] = used + 1
            if len(limited) >= self._MAX_AUTO_TAGS:
                break

        return limited
