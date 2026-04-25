from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.event_generation import EventResult
from app.core.planning import UtterancePlanResult

if TYPE_CHECKING:
    from app.clients.llm_client import LLMClient

_SYSTEM_PROMPT = (
    "あなたはゲーム実況者です。以下のルールを必ず守ってください。\n"
    "1. 1〜2文で完結させる。\n"
    "2. 口語・日本語で話す。\n"
    "3. 直前の実況と同じ表現を繰り返さない。\n"
    "4. 戦闘中は興奮気味に、平和なシーンは落ち着いたトーンで話す。"
)
_STYLE_PROMPTS = {
    "excited": "テンション高め。感嘆表現を使い、勢いのある実況にする。",
    "neutral": "フラットで聞き取りやすい語り口。状況説明を優先する。",
    "calm": "落ち着いた語り口。短く丁寧に要点を伝える。",
}


class PromptGenerator:
    """発話計画とイベントから LLM へのプロンプトを組み立てる。"""

    def build_prompt(
        self,
        plan: UtterancePlanResult,
        events: list[EventResult],
        prev_text: str = "",
    ) -> list[dict[str, str]]:
        event_summary = "\n".join(self._format_event_line(e) for e in events)
        style_rule = _STYLE_PROMPTS.get(plan.style, _STYLE_PROMPTS["neutral"])
        user_content = (
            f"スタイル: {plan.style}\n"
            f"スタイル指示: {style_rule}\n"
            f"ゲームイベント:\n{event_summary or '(情報なし)'}\n"
        )
        if prev_text:
            user_content += f"直前の実況: 「{prev_text}」\n"
            user_content += "直前の文と同じ語尾・同じ言い回しは使わないでください。\n"
        user_content += "上記を踏まえて実況してください。"

        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    def _format_event_line(self, event: EventResult) -> str:
        summary = event.details.get("scene_summary", "") if isinstance(event.details, dict) else ""
        return (
            f"- [{event.event_type}] {summary} "
            f"(importance={event.importance:.2f}, emotion={event.emotion_hint})"
        )


class CommentaryService:
    """LLM を使って実況文を生成する。"""

    def __init__(self, prompt_generator: PromptGenerator | None = None) -> None:
        self.prompt_generator = prompt_generator or PromptGenerator()

    def generate(
        self,
        plan: UtterancePlanResult,
        events: list[EventResult],
        llm_client: LLMClient,
        prev_text: str = "",
    ) -> dict[str, Any]:
        """実況文を生成して返す。"""
        messages = self.prompt_generator.build_prompt(plan, events, prev_text)
        result = llm_client.complete(messages)
        return {
            "text": result["text"],
            "style": plan.style,
            "language": "japanese",
            "llm_raw_response": result.get("raw", {}),
        }
