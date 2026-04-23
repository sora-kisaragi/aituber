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
        if "攻撃" in analysis.actions or "kill" in analysis.actions:
            score = min(1.0, score + 0.2)
        return round(score, 2)

    def _infer_type(self, analysis: VisionAnalysis) -> str:
        actions = [a.lower() for a in analysis.actions]
        if any(a in actions for a in ["kill", "攻撃", "attack"]):
            return "combat"
        if any(a in actions for a in ["score", "goal", "得点"]):
            return "score_change"
        return "scene_change"

    def _emotion_hint(self, importance: float) -> str:
        for threshold, hint in self._EMOTION_MAP:
            if importance >= threshold:
                return hint
        return "calm"
