from app.core.tags import (
    build_tag_source_map,
    mark_llm_tag_status_skipped,
    normalize_video_metadata,
)


def test_mark_llm_tag_status_skipped_when_called_sets_skipped_status_and_error() -> None:
    metadata = {
        "tags_auto_llm": ["game:zelda"],
        "tag_status": {"rule": "ready", "llm": "pending", "llm_error": None},
    }

    refreshed = mark_llm_tag_status_skipped(metadata)

    assert refreshed["tags_auto_llm"] == ["game:zelda"]
    assert refreshed["tag_status"]["rule"] == "ready"
    assert refreshed["tag_status"]["llm"] == "skipped"
    assert refreshed["tag_status"]["llm_error"] == "LLMTagger 未実装のためスキップしました"


def test_build_tag_source_map_when_tags_exist_returns_expected_sources() -> None:
    metadata = {
        "tags_manual": ["genre:rpg"],
        "tags_auto_rule": ["cfg:tts_mode:custom_voice"],
        "tags_auto_llm": ["game:elden_ring"],
        "tags_suggested_llm": ["candidate:dragon_quest"],
    }

    source_map = build_tag_source_map(metadata)

    assert source_map["genre:rpg"] == "manual"
    assert source_map["cfg:tts_mode:custom_voice"] == "rule"
    assert source_map["game:elden_ring"] == "llm"
    assert source_map["candidate:dragon_quest"] == "llm_suggested"


def test_normalize_video_metadata_when_metadata_is_none_returns_default_structure() -> None:
    result = normalize_video_metadata(None)

    assert result["tags_manual"] == []
    assert result["tags_auto_rule"] == []
    assert result["tags_auto_llm"] == []
    assert result["tags_suggested_llm"] == []
    assert result["tags_effective"] == []
    assert result["tag_status"] == {"rule": "pending", "llm": "pending", "llm_error": None}
