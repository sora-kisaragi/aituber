"""test_videos_manual_tags モジュール。"""

from app.api.videos import _normalize_tags


def test_normalize_tags_when_prefix_missing_adds_topic_prefix() -> None:
    """test_normalize_tags_when_prefix_missing_adds_topic_prefix の動作を検証する。

    Args:
        なし。

    Returns:
        なし。プレフィックス未指定時に `topic:` が補完されることを検証する。
    """
    result = _normalize_tags(["boss戦", "  clutch ", ""])

    assert result == ["topic:boss戦", "topic:clutch"]


def test_normalize_tags_when_prefixed_and_non_prefixed_are_mixed_deduplicates() -> None:
    """test_normalize_tags_when_prefixed_and_non_prefixed_are_mixed_deduplicates の動作を検証する。

    Args:
        なし。

    Returns:
        なし。補完後の重複が除外されることを検証する。
    """
    result = _normalize_tags(["boss戦", "topic:boss戦", "genre:rpg"])

    assert result == ["topic:boss戦", "genre:rpg"]
