"""UtterancePlanner の発話抑制ロジックを検証する。"""

from app.core.event_generation import EventResult
from app.core.planning import UtterancePlanner


def _make_event(
    timestamp: float,
    importance: float = 0.7,
    event_type: str = "scene_change",
) -> EventResult:
    """テスト用 EventResult を生成する。

    Args:
        timestamp: イベント発生時刻（秒）。
        importance: イベント重要度。
        event_type: イベント種別。

    Returns:
        テスト用の `EventResult`。
    """
    return EventResult(
        event_id="evt-1",
        timestamp=timestamp,
        event_type=event_type,
        importance=importance,
        emotion_hint="neutral",
        speak_recommended=True,
    )


class TestUtterancePlanner:
    """UtterancePlanner テスト。"""

    def setup_method(self) -> None:
        """各テスト前にデフォルトプランナーを準備する。

        Args:
            なし。

        Returns:
            なし。デフォルト設定の planner を初期化する。
        """
        self.planner = UtterancePlanner(min_silence_seconds=2.0, plan_duration=3.0)

    def test_plan_generates_plans(self) -> None:
        """離れたイベント2件から2件の計画が生成されることを確認する。

        Args:
            なし。

        Returns:
            なし。離れた2イベントが2計画に変換されることを検証する。
        """
        events = [_make_event(0.0), _make_event(10.0)]
        plans = self.planner.plan("vid-1", events)
        assert len(plans) == 2

    def test_silence_suppression(self) -> None:
        """無音制約により連続イベントが抑制されることを確認する。

        Args:
            なし。

        Returns:
            なし。最小無音時間制約で後続が抑制されることを検証する。
        """
        events = [_make_event(0.0), _make_event(1.0)]
        plans = self.planner.plan("vid-1", events)
        assert len(plans) == 1

    def test_style_excited_for_high_importance(self) -> None:
        """高重要度イベントで excited スタイルが選択されることを確認する。

        Args:
            なし。

        Returns:
            なし。高重要度で `excited` が選ばれることを検証する。
        """
        events = [_make_event(0.0, importance=0.9)]
        plans = self.planner.plan("vid-1", events)
        assert plans[0].style == "excited"

    def test_speak_not_recommended_skipped(self) -> None:
        """speak_recommended=False のイベントが除外されることを確認する。

        Args:
            なし。

        Returns:
            なし。`speak_recommended=False` が除外されることを検証する。
        """
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
        """重要度閾値未満のイベントが除外されることを確認する。

        Args:
            なし。

        Returns:
            なし。閾値未満イベントが除外されることを検証する。
        """
        planner = UtterancePlanner(
            min_silence_seconds=0.0,
            plan_duration=2.0,
            speak_threshold=0.6,
        )
        events = [_make_event(0.0, importance=0.5)]
        plans = planner.plan("vid-1", events)
        assert len(plans) == 0

    def test_start_time_shifted_when_overlap_would_happen(self) -> None:
        """重複回避のため開始時刻が後ろへシフトすることを確認する。

        Args:
            なし。

        Returns:
            なし。重複回避で開始時刻が後ろへ調整されることを検証する。
        """
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
        """発話率上限を超える計画が抑制されることを確認する。

        Args:
            なし。

        Returns:
            なし。発話率制限で計画が抑制されることを検証する。
        """
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

    def test_same_event_type_within_cooldown_is_suppressed(self) -> None:
        """同一イベント種別の連続発話がクールダウンで抑制されることを確認する。

        Args:
            なし。

        Returns:
            なし。同種イベントのクールダウン抑制を検証する。
        """
        planner = UtterancePlanner(
            min_silence_seconds=0.0,
            plan_duration=1.0,
            max_queue_delay_seconds=10.0,
            event_cooldown_seconds=5.0,
        )
        events = [
            _make_event(0.0, importance=0.9, event_type="combat"),
            _make_event(2.0, importance=0.95, event_type="combat"),
            _make_event(7.0, importance=0.95, event_type="combat"),
        ]
        plans = planner.plan("vid-1", events)
        assert len(plans) == 2
        assert plans[0].start_time == 0.0
        assert plans[1].start_time == 7.0

    def test_different_event_types_are_not_suppressed_by_cooldown(self) -> None:
        """異なるイベント種別はクールダウン対象外であることを確認する。

        Args:
            なし。

        Returns:
            なし。異種イベントはクールダウン抑制対象外であることを検証する。
        """
        planner = UtterancePlanner(
            min_silence_seconds=0.0,
            plan_duration=1.0,
            max_queue_delay_seconds=10.0,
            event_cooldown_seconds=10.0,
        )
        events = [
            _make_event(0.0, importance=0.9, event_type="combat"),
            _make_event(2.0, importance=0.9, event_type="score_change"),
        ]
        plans = planner.plan("vid-1", events)
        assert len(plans) == 2
