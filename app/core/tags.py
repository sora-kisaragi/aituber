"""tags モジュール。"""

from __future__ import annotations

from typing import Any

# システム由来タグ（設定・動画メタ情報）
SYSTEM_TAG_PREFIXES: tuple[str, ...] = (
    "cfg:tts_mode:",
    "cfg:llm_model:",
    "cfg:vlm_model:",
    "video:length:",
    "video:fps:",
)

# 内容由来タグ（解析結果）
CONTENT_TAG_PREFIXES: tuple[str, ...] = (
    "category:",
    "genre:",
    "game:",
    "topic:",
    "scene:",
    "situation:",
    "place:",
    "environment:",
    "time:",
    "weather:",
    "candidate:",
)

TAG_TAXONOMY: dict[str, list[str]] = {
    "system": list(SYSTEM_TAG_PREFIXES),
    "content": list(CONTENT_TAG_PREFIXES),
}

_DEFAULT_STATUS = {
    "rule": "pending",
    "llm": "pending",
    "llm_error": None,
}
_ALLOWED_STATUS = {"pending", "ready", "error", "skipped"}


def normalize_video_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """動画メタデータのタグ関連キーを正規化して返す。

    Args:
        metadata: DB から取得した生メタデータ。`None` や欠損キーを許容する。

    Returns:
        タグ関連キーを補完・正規化したメタデータ辞書。
    """
    raw = metadata if isinstance(metadata, dict) else {}

    tags_manual = normalize_tags(raw.get("tags_manual"))
    tags_auto_rule = normalize_tags(raw.get("tags_auto_rule"))
    tags_auto_llm = normalize_tags(raw.get("tags_auto_llm"))
    tags_suggested_llm = normalize_tags(raw.get("tags_suggested_llm"))
    tag_status = normalize_tag_status(raw.get("tag_status"))
    tags_effective = merge_effective_tags(tags_manual, tags_auto_rule, tags_auto_llm)

    normalized = dict(raw)
    normalized.update(
        {
            "tags_manual": tags_manual,
            "tags_auto_rule": tags_auto_rule,
            "tags_auto_llm": tags_auto_llm,
            "tags_suggested_llm": tags_suggested_llm,
            "tags_effective": tags_effective,
            "tag_status": tag_status,
        }
    )
    return normalized


def normalize_tags(value: Any) -> list[str]:
    """タグ配列を重複除去・空要素除去して正規化する。

    Args:
        value: タグ配列想定の値。リスト以外や不正要素を含んでも受け付ける。

    Returns:
        taxonomy に含まれる有効タグだけを残した重複なし配列。
    """
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_tag in value:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip()
        if not tag or tag in seen or not is_taxonomy_tag(tag):
            continue
        normalized.append(tag)
        seen.add(tag)
    return normalized


def normalize_tag_status(value: Any) -> dict[str, str | None]:
    """タグ処理ステータスを既定値付きで正規化する。

    Args:
        value: `tag_status` 想定の値。辞書でない場合は既定値を返す。

    Returns:
        `rule`/`llm`/`llm_error` を安全に補完したステータス辞書。
    """
    status = dict(_DEFAULT_STATUS)
    if not isinstance(value, dict):
        return status

    for key in ("rule", "llm"):
        raw = value.get(key)
        if isinstance(raw, str) and raw in _ALLOWED_STATUS:
            status[key] = raw

    llm_error = value.get("llm_error")
    if isinstance(llm_error, str):
        stripped = llm_error.strip()
        status["llm_error"] = stripped if stripped else None
    return status


def merge_effective_tags(
    tags_manual: list[str],
    tags_auto_rule: list[str],
    tags_auto_llm: list[str],
) -> list[str]:
    """manual > rule > llm 優先で tags_effective を合成する。

    Args:
        tags_manual: ユーザーが手動編集したタグ群（最優先）。
        tags_auto_rule: ルールベース推定タグ群（中優先）。
        tags_auto_llm: LLM 推定タグ群（低優先）。

    Returns:
        タグ族ごとに優先順位を適用した統合タグ配列。
    """
    family_map: dict[str, str] = {}

    # 先に低優先を入れ、高優先で上書きする。
    for source_tags in (tags_auto_llm, tags_auto_rule, tags_manual):
        for tag in source_tags:
            family_map[_tag_family(tag)] = tag

    return list(family_map.values())


def is_taxonomy_tag(tag: str) -> bool:
    """定義済み taxonomy（system/content）に含まれるタグか判定する。

    Args:
        tag: 判定対象のタグ文字列。

    Returns:
        システム由来または内容由来プレフィックスに一致する場合は `True`。
    """
    return tag.startswith(SYSTEM_TAG_PREFIXES) or tag.startswith(CONTENT_TAG_PREFIXES)


def _tag_family(tag: str) -> str:
    """優先順位解決に使うタグ族キーを返す。

    Args:
        tag: `prefix:value` 形式を想定したタグ文字列。

    Returns:
        優先順位解決時に比較する族キー。
    """
    parts = tag.split(":")
    if len(parts) <= 1:
        return tag
    if len(parts) == 2:
        return parts[0]
    return ":".join(parts[:-1])


def build_tag_source_map(metadata: dict[str, Any]) -> dict[str, str]:
    """タグがどのソース由来かを返す。

    Args:
        metadata: タグ関連情報を含む動画メタデータ。

    Returns:
        `tag -> source` の対応辞書。source は `manual`/`rule`/`llm` など。
    """
    normalized = normalize_video_metadata(metadata)
    source_map: dict[str, str] = {}
    for tag in normalized.get("tags_auto_llm", []):
        source_map[tag] = "llm"
    for tag in normalized.get("tags_auto_rule", []):
        source_map[tag] = "rule"
    for tag in normalized.get("tags_manual", []):
        source_map[tag] = "manual"
    for tag in normalized.get("tags_suggested_llm", []):
        source_map.setdefault(tag, "llm_suggested")
    return source_map


def mark_llm_tag_status_skipped(
    metadata: dict[str, Any] | None,
    error_message: str = "LLMTagger 未実装のためスキップしました",
) -> dict[str, Any]:
    """LLM タグ更新をスキップ扱いにして状態を返す。

    Args:
        metadata: 更新対象メタデータ。`None` の場合は空メタデータから開始する。
        error_message: スキップ理由として `tag_status.llm_error` に格納する文言。

    Returns:
        `llm` を `skipped` に設定した正規化済みメタデータ。
    """
    normalized = normalize_video_metadata(metadata)
    tag_status = dict(normalized.get("tag_status", {}))
    tag_status["llm"] = "skipped"
    tag_status["llm_error"] = error_message
    normalized["tag_status"] = tag_status
    return normalize_video_metadata(normalized)
