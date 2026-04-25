from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.vision import VisionAnalysis


@dataclass
class EventResult:
    event_id: str
    timestamp: float
    event_type: str
    importance: float
    emotion_hint: str
    speak_recommended: bool
    details: dict[str, Any] = field(default_factory=dict)


class EventService:
    """VLM 解析結果からゲームイベントを生成する。"""

    # importance 閾値ごとの emotion_hint マッピング
    _EMOTION_MAP: list[tuple[float, str]] = [
        (0.8, "excited"),
        (0.5, "neutral"),
        (0.0, "calm"),
    ]
    _KILL_KEYWORDS = ("kill", "撃破", "討伐", "倒し", "elimination")
    _DEATH_KEYWORDS = ("death", "dead", "倒され", "やられ", "被弾死")
    _LEVEL_UP_KEYWORDS = ("level_up", "level up", "ランクアップ", "昇格", "進化")
    _SCORE_KEYWORDS = ("score", "goal", "得点", "ポイント", "capture", "objective")
    _COMBAT_KEYWORDS = ("attack", "combat", "fight", "battle", "攻撃", "戦闘", "交戦")
    _CALM_KEYWORDS = ("menu", "idle", "waiting", "待機", "移動", "探索")

    def generate(
        self,
        segment_id: str,
        segment_start_time: float,
        frame_analyses: list[VisionAnalysis],
    ) -> list[EventResult]:
        """セグメントのフレーム解析からイベントを生成する。最低 1 件を保証する。"""
        events: list[EventResult] = []

        for analysis in frame_analyses:
            importance = self._calc_importance(analysis)
            events.append(
                EventResult(
                    event_id=str(uuid.uuid4()),
                    timestamp=segment_start_time,
                    event_type=self._infer_type(analysis),
                    importance=importance,
                    emotion_hint=self._emotion_hint(importance),
                    speak_recommended=importance >= 0.3,
                    details={
                        "scene_summary": analysis.scene_summary,
                        "objects": analysis.objects,
                        "actions": analysis.actions,
                    },
                )
            )

        # フレームが存在しない場合でもデフォルトイベントを生成
        if not events:
            events.append(
                EventResult(
                    event_id=str(uuid.uuid4()),
                    timestamp=segment_start_time,
                    event_type="scene_change",
                    importance=0.5,
                    emotion_hint="neutral",
                    speak_recommended=True,
                    details={},
                )
            )

        return events

    def _calc_importance(self, analysis: VisionAnalysis) -> float:
        score = analysis.confidence
        action_text = " ".join(str(a).lower() for a in analysis.actions)
        summary_text = (analysis.scene_summary or "").lower()
        combined = f"{action_text} {summary_text}"

        if any(keyword in combined for keyword in self._KILL_KEYWORDS):
            score += 0.25
        elif any(keyword in combined for keyword in self._DEATH_KEYWORDS):
            score += 0.2
        elif any(keyword in combined for keyword in self._LEVEL_UP_KEYWORDS):
            score += 0.18
        elif any(keyword in combined for keyword in self._SCORE_KEYWORDS):
            score += 0.15
        elif any(keyword in combined for keyword in self._COMBAT_KEYWORDS):
            score += 0.12

        if any(keyword in combined for keyword in self._CALM_KEYWORDS):
            score -= 0.1

        score = max(0.0, min(1.0, score))
        return round(score, 2)

    def _infer_type(self, analysis: VisionAnalysis) -> str:
        action_text = " ".join(str(a).lower() for a in analysis.actions)
        summary_text = (analysis.scene_summary or "").lower()
        combined = f"{action_text} {summary_text}"

        if any(keyword in combined for keyword in self._KILL_KEYWORDS):
            return "kill"
        if any(keyword in combined for keyword in self._DEATH_KEYWORDS):
            return "death"
        if any(keyword in combined for keyword in self._LEVEL_UP_KEYWORDS):
            return "level_up"
        if any(keyword in combined for keyword in self._SCORE_KEYWORDS):
            return "score_change"
        if any(keyword in combined for keyword in self._COMBAT_KEYWORDS):
            return "combat"
        return "scene_change"

    def _emotion_hint(self, importance: float) -> str:
        for threshold, hint in self._EMOTION_MAP:
            if importance >= threshold:
                return hint
        return "calm"
