from app.core.tags import merge_effective_tags, normalize_tags, normalize_video_metadata


def test_merge_effective_tags_applies_manual_rule_llm_priority() -> None:
    manual = ["genre:rpg", "cfg:tts_mode:custom_voice"]
    rule = ["genre:action", "video:fps:60"]
    llm = ["genre:strategy", "game:elden_ring"]

    effective = merge_effective_tags(manual, rule, llm)

    assert "genre:rpg" in effective
    assert "genre:action" not in effective
    assert "genre:strategy" not in effective
    assert "cfg:tts_mode:custom_voice" in effective
    assert "video:fps:60" in effective
    assert "game:elden_ring" in effective


def test_normalize_video_metadata_sets_required_keys_and_effective_tags() -> None:
    metadata = {
        "tags_manual": ["genre:racing"],
        "tags_auto_rule": ["cfg:tts_mode:voice_design"],
        "tags_auto_llm": ["game:mario_kart"],
        "extra": "keep",
    }

    normalized = normalize_video_metadata(metadata)

    assert normalized["extra"] == "keep"
    assert normalized["tags_manual"] == ["genre:racing"]
    assert normalized["tags_auto_rule"] == ["cfg:tts_mode:voice_design"]
    assert normalized["tags_auto_llm"] == ["game:mario_kart"]
    assert normalized["tags_suggested_llm"] == []
    assert normalized["tag_status"] == {"rule": "pending", "llm": "pending", "llm_error": None}
    assert set(normalized["tags_effective"]) == {
        "cfg:tts_mode:voice_design",
        "game:mario_kart",
        "genre:racing",
    }


def test_normalize_tags_filters_unknown_and_duplicate_tags() -> None:
    raw = [
        " genre:rpg ",
        "genre:rpg",
        "unknown_tag",
        "game:elden_ring",
        "",
        123,
    ]

    normalized = normalize_tags(raw)

    assert normalized == ["genre:rpg", "game:elden_ring"]
