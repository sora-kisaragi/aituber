from app.core.event_generation import EventResult
from app.core.planning import UtterancePlanResult
from app.core.prompt import PromptGenerator


def _plan(style: str) -> UtterancePlanResult:
    return UtterancePlanResult(
        plan_id="plan-1",
        video_id="video-1",
        event_ids=["evt-1"],
        start_time=0.0,
        end_time=3.0,
        priority=3,
        style=style,
    )


def _event() -> EventResult:
    return EventResult(
        event_id="evt-1",
        timestamp=0.0,
        event_type="combat",
        importance=0.87,
        emotion_hint="excited",
        speak_recommended=True,
        details={"scene_summary": "敵と交戦中"},
    )


def test_build_prompt_when_excited_style_includes_style_instruction() -> None:
    prompt = PromptGenerator().build_prompt(_plan("excited"), [_event()])
    user_message = next(m["content"] for m in prompt if m["role"] == "user")
    assert "スタイル: excited" in user_message
    assert "テンション高め" in user_message
    assert "[combat]" in user_message


def test_build_prompt_when_prev_text_exists_includes_non_repeat_instruction() -> None:
    prompt = PromptGenerator().build_prompt(_plan("neutral"), [_event()], prev_text="すごい展開だ！")
    user_message = next(m["content"] for m in prompt if m["role"] == "user")
    assert "直前の実況" in user_message
    assert "同じ語尾・同じ言い回しは使わない" in user_message
