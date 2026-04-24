import pytest

from app.core.llm_tagger import LLMTagger


class DummyLLMClient:
    def __init__(self, text: str) -> None:
        self._text = text
        self.messages: list[dict[str, str]] = []

    def complete(self, messages: list[dict[str, str]]) -> dict:
        self.messages = messages
        return {"text": self._text, "raw": {}}


def test_generate_when_json_response_returns_normalized_tags() -> None:
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
    client = DummyLLMClient("not-json")

    with pytest.raises(ValueError, match="JSON 解析に失敗"):
        LLMTagger().generate(
            video_title="Broken",
            current_tags=[],
            llm_client=client,
        )
