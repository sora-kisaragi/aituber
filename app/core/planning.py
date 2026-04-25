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

    連続発話を抑制し、無言時間を許可しながら importance に応じてスタイルを決定する。
    """

    # importance → style マッピング（閾値の降順）
    _STYLE_MAP: list[tuple[float, str]] = [
        (0.8, "excited"),
        (0.5, "neutral"),
        (0.0, "calm"),
    ]

    def __init__(
        self,
        min_silence_seconds: float = 2.0,
        plan_duration: float = 3.0,
        speak_threshold: float = 0.3,
        max_talk_ratio: float = 0.5,
        talk_window_seconds: float = 60.0,
        max_queue_delay_seconds: float = 3.0,
        event_cooldown_seconds: float = 4.0,
    ) -> None:
        self.min_silence_seconds = max(0.0, min_silence_seconds)
        self.plan_duration = max(0.1, plan_duration)
        self.speak_threshold = max(0.0, min(1.0, speak_threshold))
        self.max_talk_ratio = max(0.0, min(1.0, max_talk_ratio))
        self.talk_window_seconds = max(1.0, talk_window_seconds)
        self.max_queue_delay_seconds = max(0.0, max_queue_delay_seconds)
        self.event_cooldown_seconds = max(0.0, event_cooldown_seconds)

    def plan(self, video_id: str, events: list[EventResult]) -> list[UtterancePlanResult]:
        """speak_recommended なイベントから発話計画を生成する。"""
        candidates = [event for event in events if event.speak_recommended]
        candidates = self._deduplicate_same_timestamp(candidates)
        candidates.sort(key=lambda e: e.timestamp)

        plans: list[UtterancePlanResult] = []
        last_end_time = -self.min_silence_seconds
        last_spoken_by_type: dict[str, float] = {}

        for event in candidates:
            effective_threshold = self._resolve_threshold(len(plans))
            if event.importance < effective_threshold:
                continue
            # 重複を回避するため、開始時刻を「前発話終了 + 無言時間」以降に寄せる。
            start_time = max(event.timestamp, last_end_time + self.min_silence_seconds)
            queue_delay = start_time - event.timestamp
            if queue_delay > self.max_queue_delay_seconds:
                continue

            if self._in_event_cooldown(event.event_type, start_time, last_spoken_by_type):
                continue

            end_time = start_time + self.plan_duration
            if self._would_exceed_talk_ratio(plans, start_time, end_time):
                continue

            plans.append(
                UtterancePlanResult(
                    plan_id=str(uuid.uuid4()),
                    video_id=video_id,
                    event_ids=[event.event_id],
                    start_time=start_time,
                    end_time=end_time,
                    priority=self._calc_priority(event.importance),
                    style=self._resolve_style(event.importance),
                )
            )
            last_end_time = end_time
            last_spoken_by_type[event.event_type] = start_time

        return plans

    def _deduplicate_same_timestamp(self, events: list[EventResult]) -> list[EventResult]:
        """同一 timestamp の候補が複数ある場合は importance が最大の 1 件に絞る。"""
        best_by_timestamp: dict[float, EventResult] = {}
        for event in events:
            current = best_by_timestamp.get(event.timestamp)
            if current is None or event.importance > current.importance:
                best_by_timestamp[event.timestamp] = event
        return list(best_by_timestamp.values())

    def _would_exceed_talk_ratio(
        self,
        accepted_plans: list[UtterancePlanResult],
        new_start_time: float,
        new_end_time: float,
    ) -> bool:
        """直近ウィンドウの発話率上限を超える場合は True を返す。"""
        window_start = max(0.0, new_start_time - self.talk_window_seconds)
        spoken_seconds = 0.0

        for plan in accepted_plans:
            overlap_start = max(window_start, plan.start_time)
            overlap_end = min(new_start_time, plan.end_time)
            if overlap_end > overlap_start:
                spoken_seconds += overlap_end - overlap_start

        projected = spoken_seconds + max(0.0, new_end_time - new_start_time)
        return (projected / self.talk_window_seconds) > self.max_talk_ratio

    def _resolve_style(self, importance: float) -> str:
        for threshold, style in self._STYLE_MAP:
            if importance >= threshold:
                return style
        return "calm"

    def _resolve_threshold(self, accepted_count: int) -> float:
        """連続発話が増えたら閾値を段階的に上げる。"""
        if accepted_count >= 8:
            return min(1.0, self.speak_threshold + 0.2)
        if accepted_count >= 4:
            return min(1.0, self.speak_threshold + 0.1)
        return self.speak_threshold

    def _in_event_cooldown(
        self,
        event_type: str,
        start_time: float,
        last_spoken_by_type: dict[str, float],
    ) -> bool:
        last_time = last_spoken_by_type.get(event_type)
        if last_time is None:
            return False
        return (start_time - last_time) < self.event_cooldown_seconds

    def _calc_priority(self, importance: float) -> int:
        return max(1, min(5, int(importance * 5)))
