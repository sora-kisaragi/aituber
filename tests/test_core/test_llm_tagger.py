"""test_llm_tagger モジュール。"""

import pytest

from app.core.llm_tagger import LLMTagger


class DummyLLMClient:
    """DummyLLMClient を表すクラス。"""

    def __init__(self, text: str) -> None:
        """インスタンスを初期化する。

        Args:
            text: `complete` 呼び出し時に返す固定レスポンステキスト。

        Returns:
            なし。検証用の状態を初期化する。
        """
        self._text = text
        self.messages: list[dict[str, str]] = []

    def complete(self, messages: list[dict[str, str]]) -> dict:
        """complete を実行する。

        Args:
            messages: 呼び出し元が組み立てたプロンプトメッセージ配列。

        Returns:
            `text` に固定値を返すモックレスポンス。
        """
        self.messages = messages
        return {"text": self._text, "raw": {}}


def test_generate_when_json_response_returns_normalized_tags() -> None:
    """test_generate_when_json_response_returns_normalized_tags の動作を検証する。

    Args:
        なし。

    Returns:
        なし。JSON 応答の正規化結果を検証する。
    """
    client = DummyLLMClient(
        '{"tags_auto_llm": ["Genre:RPG", "game:Elden Ring", "topic:Boss Fight", '
        '"candidate:ignored"], "tags_suggested_llm": ["Dragon Quest", '
        '"candidate:Final Fantasy", "game:Zelda"]}'
    )

    result = LLMTagger().generate(
        video_title="Boss Battle",
        current_tags=["genre:action", "cfg:tts_mode:custom_voice"],
        llm_client=client,
    )

    assert result["tags_auto_llm"] == ["genre:rpg", "game:elden_ring", "topic:boss_fight"]
    assert result["tags_suggested_llm"] == [
        "candidate:dragon_quest",
        "candidate:final_fantasy",
        "candidate:zelda",
    ]
    assert any(message["role"] == "system" for message in client.messages)
    assert any("動画タイトル: Boss Battle" in message["content"] for message in client.messages)


def test_generate_when_fenced_json_response_extracts_payload() -> None:
    """test_generate_when_fenced_json_response_extracts_payload の動作を検証する。

    Args:
        なし。

    Returns:
        なし。コードフェンス付き JSON の抽出を検証する。
    """
    client = DummyLLMClient(
        "```json\n"
        '{"tags_auto_llm": ["topic:strategy"], "tags_suggested_llm": ["Metaphor ReFantazio"]}'
        "\n```"
    )

    result = LLMTagger().generate(
        video_title="Strategy Guide",
        current_tags=[],
        llm_client=client,
    )

    assert result == {
        "tags_auto_llm": ["topic:strategy"],
        "tags_suggested_llm": ["candidate:metaphor_refantazio"],
    }


def test_generate_when_non_json_response_raises_value_error() -> None:
    """test_generate_when_non_json_response_raises_value_error の動作を検証する。

    Args:
        なし。

    Returns:
        なし。非 JSON 応答時の例外送出を検証する。
    """
    client = DummyLLMClient("not-json")

    with pytest.raises(ValueError, match="JSON 解析に失敗"):
        LLMTagger().generate(
            video_title="Broken",
            current_tags=[],
            llm_client=client,
        )


def test_generate_when_extended_prefixes_exist_returns_normalized_auto_tags() -> None:
    """test_generate_when_extended_prefixes_exist_returns_normalized_auto_tags の動作を検証する。

    Args:
        なし。

    Returns:
        なし。拡張プレフィックスの受理を検証する。
    """
    client = DummyLLMClient(
        '{"tags_auto_llm": ["scene:Boss Intro", "situation:clutch", "place:urban city", '
        '"environment:outdoor", "time:night", "weather:rainy"], "tags_suggested_llm": []}'
    )

    result = LLMTagger().generate(
        video_title="Night Battle",
        current_tags=["genre:action"],
        llm_client=client,
    )

    assert result["tags_auto_llm"] == [
        "scene:boss_intro",
        "situation:clutch",
        "place:urban_city",
        "environment:outdoor",
        "time:night",
        "weather:rainy",
    ]
    assert result["tags_suggested_llm"] == []


def test_generate_when_noise_values_exist_filters_them_out() -> None:
    """test_generate_when_noise_values_exist_filters_them_out の動作を検証する。

    Args:
        なし。

    Returns:
        なし。`unknown` / `other` 系ノイズ除外を検証する。
    """
    client = DummyLLMClient(
        '{"tags_auto_llm": ["genre:unknown", "topic:other", "scene:boss_fight"], '
        '"tags_suggested_llm": ["candidate:unknown", "Final Boss"]}'
    )

    result = LLMTagger().generate(
        video_title="Noise",
        current_tags=[],
        llm_client=client,
    )

    assert result["tags_auto_llm"] == ["scene:boss_fight"]
    assert result["tags_suggested_llm"] == ["candidate:final_boss"]


def test_generate_when_same_prefix_too_many_limits_auto_tags_per_prefix() -> None:
    """test_generate_when_same_prefix_too_many_limits_auto_tags_per_prefix の動作を検証する。

    Args:
        なし。

    Returns:
        なし。同一プレフィックスが上限件数に制限されることを検証する。
    """
    client = DummyLLMClient(
        '{"tags_auto_llm": ["topic:a", "topic:b", "topic:c", "topic:d", "topic:e"], '
        '"tags_suggested_llm": []}'
    )

    result = LLMTagger().generate(
        video_title="Topic Heavy",
        current_tags=[],
        llm_client=client,
    )

    assert result["tags_auto_llm"] == ["topic:a", "topic:b", "topic:c"]
