"""test_tags モジュール。"""

from app.core.tags import merge_effective_tags, normalize_tags, normalize_video_metadata


def test_merge_effective_tags_applies_manual_rule_llm_priority() -> None:
    """test_merge_effective_tags_applies_manual_rule_llm_priority の動作を検証する。

    Args:
        なし。

    Returns:
        なし。manual > rule > llm 優先順が適用されることを検証する。
    """
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
    """test_normalize_video_metadata_sets_required_keys_and_effective_tags の動作を検証する。

    Args:
        なし。

    Returns:
        なし。不足キー補完と `tags_effective` 合成を検証する。
    """
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
    """test_normalize_tags_filters_unknown_and_duplicate_tags の動作を検証する。

    Args:
        なし。

    Returns:
        なし。未知タグ・重複タグ・非文字列が除外されることを検証する。
    """
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


def test_normalize_tags_when_extended_content_prefixes_returns_valid_items() -> None:
    """test_normalize_tags_when_extended_content_prefixes_returns_valid_items の動作を検証する。

    Args:
        なし。

    Returns:
        なし。拡張した content 系プレフィックスが受理されることを検証する。
    """
    raw = [
        "scene:boss_intro",
        "situation:clutch",
        "place:castle",
        "environment:outdoor",
        "time:night",
        "weather:rainy",
    ]

    normalized = normalize_tags(raw)

    assert normalized == [
        "scene:boss_intro",
        "situation:clutch",
        "place:castle",
        "environment:outdoor",
        "time:night",
        "weather:rainy",
    ]
