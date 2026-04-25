"""EventService のイベント種別・重要度推定を検証する。"""

from app.core.event_generation import EventService
from app.core.vision import VisionAnalysis


class TestEventService:
    """EventService テスト。"""

    def setup_method(self) -> None:
        """各テスト前にサービスを初期化する。

        Args:
            なし。

        Returns:
            なし。各テストで使う `EventService` を初期化する。
        """
        self.service = EventService()

    def test_generate_returns_at_least_one_event(self) -> None:
        """フレームが空でもイベントが1件以上返ることを確認する。

        Args:
            なし。

        Returns:
            なし。空入力時のフォールバック生成を検証する。
        """
        results = self.service.generate("seg-1", 0.0, [])
        assert len(results) >= 1

    def test_generate_from_analysis(self) -> None:
        """戦闘アクションを combat として推定できることを確認する。

        Args:
            なし。

        Returns:
            なし。戦闘解析から `combat` 推定されることを検証する。
        """
        analysis = VisionAnalysis(
            scene_summary="戦闘中",
            objects=["敵"],
            actions=["攻撃"],
            ui_state=[],
            confidence=0.9,
        )
        results = self.service.generate("seg-1", 2.5, [analysis])
        assert len(results) == 1
        assert results[0].event_type == "combat"
        assert results[0].speak_recommended is True

    def test_low_importance_not_recommended(self) -> None:
        """低重要度イベントは speak_recommended=False になることを確認する。

        Args:
            なし。

        Returns:
            なし。低重要度で発話非推奨になることを検証する。
        """
        analysis = VisionAnalysis(
            scene_summary="待機",
            objects=[],
            actions=[],
            ui_state=[],
            confidence=0.2,
        )
        results = self.service.generate("seg-1", 0.0, [analysis])
        assert results[0].speak_recommended is False

    def test_generate_when_kill_keyword_detected_returns_kill_type(self) -> None:
        """kill キーワードを kill 種別として推定することを確認する。

        Args:
            なし。

        Returns:
            なし。kill キーワードで種別と重要度が補正されることを検証する。
        """
        analysis = VisionAnalysis(
            scene_summary="敵を撃破した",
            objects=["enemy"],
            actions=["kill"],
            ui_state=[],
            confidence=0.5,
        )
        results = self.service.generate("seg-1", 0.0, [analysis])
        assert results[0].event_type == "kill"
        assert results[0].importance > 0.7

    def test_generate_when_death_keyword_detected_returns_death_type(self) -> None:
        """death キーワードを death 種別として推定することを確認する。

        Args:
            なし。

        Returns:
            なし。death キーワードで種別と重要度が補正されることを検証する。
        """
        analysis = VisionAnalysis(
            scene_summary="プレイヤーがやられた",
            objects=["player"],
            actions=["death"],
            ui_state=[],
            confidence=0.55,
        )
        results = self.service.generate("seg-1", 0.0, [analysis])
        assert results[0].event_type == "death"
        assert results[0].importance >= 0.7

    def test_generate_when_levelup_keyword_detected_returns_level_up_type(self) -> None:
        """level up キーワードを level_up 種別として推定することを確認する。

        Args:
            なし。

        Returns:
            なし。level up キーワードで `level_up` 推定されることを検証する。
        """
        analysis = VisionAnalysis(
            scene_summary="レベルアップ演出",
            objects=["ui"],
            actions=["level up"],
            ui_state=[],
            confidence=0.52,
        )
        results = self.service.generate("seg-1", 0.0, [analysis])
        assert results[0].event_type == "level_up"
        assert results[0].importance >= 0.65

    def test_emotion_hint_excited_for_high_importance(self) -> None:
        """高重要度イベントで excited ヒントが付くことを確認する。

        Args:
            なし。

        Returns:
            なし。高重要度で `excited` ヒントが付くことを検証する。
        """
        analysis = VisionAnalysis(
            scene_summary="ボス戦",
            objects=["ボス"],
            actions=["攻撃"],
            ui_state=[],
            confidence=0.95,
        )
        results = self.service.generate("seg-1", 0.0, [analysis])
        assert results[0].emotion_hint == "excited"
