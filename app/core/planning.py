from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.core.event_generation import EventResult


@dataclass
class UtterancePlanResult:
    plan_id: str
    video_id: str
    event_ids: list[str]
    start_time: float
    end_time: float
    priority: int
    style: str


class UtterancePlanner:
    """イベントリストから発話計画を生成する。

    連続発話を抑制し、importance に応じてスタイルを決定する。
    """

    # importance → style マッピング（閾値の降順）
    _STYLE_MAP: list[tuple[float, str]] = [
        (0.8, "excited"),
        (0.5, "neutral"),
        (0.0, "calm"),
    ]

    def __init__(self, min_silence_seconds: float = 2.0, plan_duration: float = 3.0) -> None:
        self.min_silence_seconds = min_silence_seconds
        self.plan_duration = plan_duration

    def plan(self, video_id: str, events: list[EventResult]) -> list[UtterancePlanResult]:
        """speak_recommended なイベントから発話計画を生成する。"""
        candidates = [e for e in events if e.speak_recommended]
        candidates.sort(key=lambda e: e.timestamp)

        plans: list[UtterancePlanResult] = []
        last_end_time = -self.min_silence_seconds

        for event in candidates:
            # 直前発話終了から min_silence_seconds 以上空いていない場合はスキップ
            if event.timestamp < last_end_time + self.min_silence_seconds:
                continue

            end_time = event.timestamp + self.plan_duration
            plans.append(
                UtterancePlanResult(
                    plan_id=str(uuid.uuid4()),
                    video_id=video_id,
                    event_ids=[event.event_id],
                    start_time=event.timestamp,
                    end_time=end_time,
                    priority=self._calc_priority(event.importance),
                    style=self._resolve_style(event.importance),
                )
            )
            last_end_time = end_time

        return plans

    def _resolve_style(self, importance: float) -> str:
        for threshold, style in self._STYLE_MAP:
            if importance >= threshold:
                return style
        return "calm"

    def _calc_priority(self, importance: float) -> int:
        return max(1, min(5, int(importance * 5)))
