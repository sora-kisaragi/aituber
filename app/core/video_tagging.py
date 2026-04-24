from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.llm_tagger import LLMTagger
from app.core.tags import normalize_video_metadata
from app.utils.logging import logger

if TYPE_CHECKING:
    from app.clients.llm_client import LLMClient


def refresh_llm_tags(
    *,
    video_id: str,
    video_title: str,
    raw_metadata: dict[str, Any] | None,
    llm_client: LLMClient,
) -> dict[str, Any]:
    """LLMTagger で自動タグを更新する。"""
    metadata = normalize_video_metadata(raw_metadata)
    tag_status = dict(metadata.get("tag_status", {}))

    try:
        generated = LLMTagger().generate(
            video_title=video_title,
            current_tags=metadata["tags_effective"],
            llm_client=llm_client,
        )
        metadata["tags_auto_llm"] = generated["tags_auto_llm"]
        metadata["tags_suggested_llm"] = generated["tags_suggested_llm"]
        tag_status["llm"] = "ready"
        tag_status["llm_error"] = None
    except Exception as e:
        logger.error("LLM タグ更新失敗: video_id=%s error=%s", video_id, e)
        tag_status["llm"] = "error"
        tag_status["llm_error"] = str(e)

    metadata["tag_status"] = tag_status
    return normalize_video_metadata(metadata)
