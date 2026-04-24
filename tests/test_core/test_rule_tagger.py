from app.core.rule_tagger import RuleTagger


def test_generate_returns_expected_rule_tags() -> None:
    tagger = RuleTagger()

    tags = tagger.generate(
        tts_mode="custom_voice",
        llm_model="gpt-4-turbo",
        vlm_model="gemma3:27b",
        duration_seconds=180.0,
        fps=29.97,
    )

    assert tags == [
        "cfg:tts_mode:custom_voice",
        "cfg:llm_model:gpt-4-turbo",
        "cfg:vlm_model:gemma3_27b",
        "video:length:medium",
        "video:fps:30",
    ]


def test_generate_uses_unknown_bucket_for_invalid_values() -> None:
    tagger = RuleTagger()

    tags = tagger.generate(
        tts_mode="",
        llm_model=" ",
        vlm_model="@@@",
        duration_seconds=None,
        fps=0.0,
    )

    assert tags == [
        "cfg:tts_mode:unknown",
        "cfg:llm_model:unknown",
        "cfg:vlm_model:unknown",
        "video:length:unknown",
        "video:fps:unknown",
    ]


def test_generate_length_bucket_for_short_and_long() -> None:
    tagger = RuleTagger()

    short_tags = tagger.generate(
        tts_mode="custom_voice",
        llm_model="gpt-4o-mini",
        vlm_model="gemma3:27b",
        duration_seconds=10.0,
        fps=60.0,
    )
    long_tags = tagger.generate(
        tts_mode="custom_voice",
        llm_model="gpt-4o-mini",
        vlm_model="gemma3:27b",
        duration_seconds=600.0,
        fps=60.0,
    )

    assert "video:length:short" in short_tags
    assert "video:length:long" in long_tags
