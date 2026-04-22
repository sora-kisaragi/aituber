from __future__ import annotations

from typing import Any, TYPE_CHECKING

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


class PromptGenerator:
    """発話計画とイベントから LLM へのプロンプトを組み立てる。"""

    def build_prompt(
        self,
        plan: UtterancePlanResult,
        events: list[EventResult],
        prev_text: str = "",
    ) -> list[dict[str, str]]:
        event_summary = "\n".join(
            f"- [{e.event_type}] {e.details.get('scene_summary', '')} (importance={e.importance})"
            for e in events
        )
        user_content = (
            f"スタイル: {plan.style}\n"
            f"ゲームイベント:\n{event_summary or '(情報なし)'}\n"
        )
        if prev_text:
            user_content += f"直前の実況: 「{prev_text}」\n"
        user_content += "上記を踏まえて実況してください。"

        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]


class CommentaryService:
    """LLM を使って実況文を生成する。"""

    def __init__(self, prompt_generator: PromptGenerator | None = None) -> None:
        self.prompt_generator = prompt_generator or PromptGenerator()

    def generate(
        self,
        plan: UtterancePlanResult,
        events: list[EventResult],
        llm_client: "LLMClient",
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
