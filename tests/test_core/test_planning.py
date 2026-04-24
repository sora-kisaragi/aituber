from app.core.event_generation import EventResult
from app.core.planning import UtterancePlanner


def _make_event(timestamp: float, importance: float = 0.7) -> EventResult:
    return EventResult(
        event_id="evt-1",
        timestamp=timestamp,
        event_type="scene_change",
        importance=importance,
        emotion_hint="neutral",
        speak_recommended=True,
    )


class TestUtterancePlanner:
    def setup_method(self) -> None:
        self.planner = UtterancePlanner(min_silence_seconds=2.0, plan_duration=3.0)

    def test_plan_generates_plans(self) -> None:
        events = [_make_event(0.0), _make_event(10.0)]
        plans = self.planner.plan("vid-1", events)
        assert len(plans) == 2

    def test_silence_suppression(self) -> None:
        # 連続 2 件のイベントがすぐ続く場合、2 件目は抑制される
        events = [_make_event(0.0), _make_event(1.0)]
        plans = self.planner.plan("vid-1", events)
        assert len(plans) == 1

    def test_style_excited_for_high_importance(self) -> None:
        events = [_make_event(0.0, importance=0.9)]
        plans = self.planner.plan("vid-1", events)
        assert plans[0].style == "excited"

    def test_speak_not_recommended_skipped(self) -> None:
        event = EventResult(
            event_id="e",
            timestamp=0.0,
            event_type="scene_change",
            importance=0.5,
            emotion_hint="neutral",
            speak_recommended=False,
        )
        plans = self.planner.plan("vid-1", [event])
        assert len(plans) == 0

    def test_low_importance_is_silenced_by_threshold(self) -> None:
        planner = UtterancePlanner(
            min_silence_seconds=0.0,
            plan_duration=2.0,
            speak_threshold=0.6,
        )
        events = [_make_event(0.0, importance=0.5)]
        plans = planner.plan("vid-1", events)
        assert len(plans) == 0

    def test_start_time_shifted_when_overlap_would_happen(self) -> None:
        planner = UtterancePlanner(
            min_silence_seconds=1.0,
            plan_duration=3.0,
            max_queue_delay_seconds=5.0,
        )
        events = [_make_event(0.0, importance=0.9), _make_event(1.0, importance=0.9)]
        plans = planner.plan("vid-1", events)
        assert len(plans) == 2
        assert plans[0].start_time == 0.0
        assert plans[1].start_time == 4.0

    def test_talk_ratio_limit_creates_silence(self) -> None:
        planner = UtterancePlanner(
            min_silence_seconds=0.0,
            plan_duration=3.0,
            max_talk_ratio=0.4,
            talk_window_seconds=10.0,
            max_queue_delay_seconds=0.0,
        )
        events = [
            _make_event(0.0, importance=0.9),
            _make_event(5.0, importance=0.9),
        ]
        plans = planner.plan("vid-1", events)
        assert len(plans) == 1
